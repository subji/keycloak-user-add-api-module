import json
import pymysql
import requests
import configparser

config = configparser.ConfigParser()
config.read('configuration.ini')

# Return DB Connection
def getConnection():
  db = pymysql.connect(host=config['DB']['HOST'], port=3306, user=config['DB']['USERNAME'], passwd=config['DB']['PASSWORD'], db=config['DB']['DB'], charset='utf8', autocommit=False)

  return db;

# Get AccessToken from keycloak
def getToken():
  tokenUrl = 'http://localhost:8080/auth/realms/' + config['KEYCLOAK']['REALM'] + '/protocol/openid-connect/token'

  res = requests.post(tokenUrl, data={ 
    'grant_type': 'client_credentials',
    'client_id': config['KEYCLOAK']['CLIENT_ID'], 
    'client_secret': config['KEYCLOAK']['CLIENT_SECRET'] })

  return res.json()['access_token']

# Generate body 
def makeBody():
  db = getConnection()

  cursor = db.cursor()
  cursor.execute("""
    SELECT *
      FROM T_USER u 
      LEFT JOIN (
        SELECT am.user_seq,
               GROUP_CONCAT(at.authority_type SEPARATOR ',') AS roles
          FROM T_AUTHORITIES_MAPPING am
          LEFT JOIN T_AUTHORITIES_TYPE at on am.authority_type_seq=at.authority_type_seq
         GROUP BY am.user_seq
      ) a on u.user_seq=a.user_seq
  """)

  for i, d in enumerate(cursor.fetchall()):
    param = { 'username': '', 'enabled': 'false' }

    attr = {
      'delYn': d[11],
      'userSeq': d[0],
      'userNickname': d[5],
      'duplicateLoginYn': d[7],
      'userEmailReceivedYn': d[6],
      'userJoinPathCodeSeq': d[13],
      'userLoginPlatformType': d[2],
      'lastLoginAttemptCount': d[12],
      'deleteDate': d[9].strftime('%m/%d/%Y, %H:%M:%S') if d[9] != None else None,
      'registerDate': d[8].strftime('%m/%d/%Y, %H:%M:%S') if d[8] != None else None,
      'updateDate': d[10].strftime('%m/%d/%Y, %H:%M:%S') if d[10] != None else None,
      'userJoinPathRegisterDate': d[14].strftime('%m/%d/%Y, %H:%M:%S') if d[14] != None else ''
    }

    param['attributes'] = attr
    param['realmRoles'] = list(set(d[16].split(',')))
    param['enabled'] = 'false' if d[11] == 'Y' else 'true'
    param['username'] = str(d[0]) + '(none)' if d[1] == None else d[1]

    # add email if it exist
    if d[4] != None:
      param['email'] = d[4]
      
    # add credential if it exist
    if d[3] != None:
      param['credentials'] = [{'type': 'password', 'value': d[3]}]

    accessToken = getToken()

    print('\ntoken: ', accessToken[0:10] + '...\nparam: ', param, '\n')

    addUser(param, 'bearer ' + accessToken)

# Call Keycloak Add user api 
def addUser(param, token):
  headers = { 'Content-Type': 'application/json; charset=utf-8', 'Authorization': token }
  apiUrl = 'http://localhost:8080/auth/admin/realms/' + config['KEYCLOAK']['REALM'] + '/users'

  res = requests.post(apiUrl, data=json.dumps(param), headers=headers)

  print('\n(' + str(res.status_code) + ') ' + res.text + '\n')

if __name__ == '__main__':  
  makeBody()
