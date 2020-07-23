import json
import pymysql
import requests
import configparser

from requests.api import head, request

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

# Get User Id for Role Mapping
def getUserId(username, token):
  headers = { 'Content-Type': 'application/json; charset=utf-8', 'Authorization': token }
  userUrl = 'http://localhost:8080/auth/admin/realms/' + config['KEYCLOAK']['REALM'] + '/users'

  res = requests.get(userUrl, params={ 'username': username }, headers=headers)

  print('\nGet User Id (', res.status_code, ') ', res.json(), '\n')

  return res.json()[0]['id']

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
  accessToken = getToken()

  roles = {
    'MASTER_ADMIN': '2ce4b4cd-34fe-4e99-9d32-e050695e8c4f',
    'NORMAL_USER': '2a3d6b29-4e22-42ab-9a4f-8df307ab55fe'
  }

  roleName = {
    'ADMIN': 'MASTER_ADMIN', 
    'USER': 'NORMAL_USER',
  }

  for i, d in enumerate(cursor.fetchall()):
    # if i == 1:
    param = { 'username': '', 'enabled': 'false' }

    attr = {
      'userSeq': d[0],
      'userNickname': d[5],
      'userEmailReceivedYn': d[6],
      'userJoinPathCodeSeq': d[13],
      'lastLoginAttemptCount': d[12],
      'deleteDate': d[9].strftime('%m/%d/%Y, %H:%M:%S') if d[9] != None else None,
      'registerDate': d[8].strftime('%m/%d/%Y, %H:%M:%S') if d[8] != None else None,
      'updateDate': d[10].strftime('%m/%d/%Y, %H:%M:%S') if d[10] != None else None,
      'userJoinPathRegisterDate': d[14].strftime('%m/%d/%Y, %H:%M:%S') if d[14] != None else ''
    }

    username = str(d[0]) + '(none)' if d[1] == None else d[1]

    param['attributes'] = attr
    param['username'] = username
    param['enabled'] = 'false' if d[11] == 'Y' else 'true'
    
    # identityProvider is none then NullPointerException
    if d[2] != 'local' and d[2] != None:
      param['federatedIdentities'] = [{
        'identityProvider': d[2]
      }]

    # add email if it exist
    if d[4] != None:
      param['email'] = d[4]
      
    # add credential if it exist
    if d[3] != None:
      param['credentials'] = [{'type': 'password', 'value': d[3]}]

    print('\ntoken: ', accessToken[0:10] + '...\nparam: ', param, '\n')

    addUser(param, [{ 
      'name': roleName[r], 
      'containerId': '8e957834-6be2-4d25-b413-2c56c1f8fc10',
      'id': roles[roleName[r] if r != '' else 'USER'] } for r in list(set(d[16].split(',')))], 'bearer ' + accessToken)

# Call Keycloak Add user api 
def addUser(param, roles, token):
  headers = { 'Content-Type': 'application/json; charset=utf-8', 'Authorization': token }
  apiUrl = 'http://localhost:8080/auth/admin/realms/' + config['KEYCLOAK']['REALM'] + '/users'

  res = requests.post(apiUrl, data=json.dumps(param), headers=headers)

  print('\n(' + str(res.status_code) + ') ' + res.text + '\n')

  if res.ok:
    userId = getUserId(param['username'], token)
    addRole(userId, roles, token)

# Add Role Mapping
def addRole(userId, param, token):
  headers = { 'Content-Type': 'application/json; charset=utf-8', 'Authorization': token }
  roleUrl = 'http://localhost:8080/auth/admin/realms/' + config['KEYCLOAK']['REALM'] + '/users/' + userId + '/role-mappings/clients/' + config['KEYCLOAK']['CLIENT']

  print('\nRoles: ', param, '\n')

  res = requests.post(roleUrl, data=json.dumps(param), headers=headers)
  
  print('\nAdd Role (', str(res.status_code), ') ', res.text, '\n')
  

if __name__ == '__main__':  
  makeBody()
