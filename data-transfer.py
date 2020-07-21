import pymysql
import requests
import json

# Return DB Connection
def getConnection():
  db = pymysql.connect(host = '{host}', port=3306, user='{username}', passwd='{password}', db='{database name}', charset='utf8', autocommit=False)
  cursor = db.cursor()
  cursor.execute('SELECT VERSION()')

  version = cursor.fetchone()

  print('Database version is: %s' % version)

  return db;

# Get AccessToken from keycloak
def getToken():
  tokenUrl = 'http://localhost:8080/auth/realms/{realm name}/protocol/openid-connect/token'

  res = requests.post(tokenUrl, data={ 
    'grant_type': 'client_credentials',
    'client_id': '{client id}', 
    'client_secret': '{client secret}' })

  return res.json()['access_token']

# Generate body 
def makeBody():
  db = getConnection()

  cursor = db.cursor()
  cursor.execute('SELECT * FROM T_USER')

  for i, d in enumerate(cursor.fetchall()):
    if i == 0:
      param = { 'username': '', 'enabled': 'false' }
      attr = {
        'userSeq': d[0],
        'userLoginPlatformType': d[2],
        'userEmail': d[4],
        'userNickname': d[5],
        'userEmailReceivedYn': d[6],
        'duplicateLoginYn': d[7],
        'registerDate': d[8].strftime('%m/%d/%Y, %H:%M:%S'),
        'deleteDate': d[9].strftime('%m/%d/%Y, %H:%M:%S'),
        'updateDate': d[10].strftime('%m/%d/%Y, %H:%M:%S'),
        'delYn': d[11],
        'lastLoginAttemptCount': d[12],
        'userJoinPathCodeSeq': d[13],
        'userJoinPathRegisterDate': d[14].strftime('%m/%d/%Y, %H:%M:%S') if d[14] != None else ''
      }
      credential = [{ 'type': 'password', 'value': d[3] }]

      param['attributes'] = attr;
      param['username'] = str(d[1])
      param['enabled'] = 'false' if d[11] == 'Y' else 'true'

      if d[3] != None:
        param['credentials'] = credential

      accessToken = getToken()

      print(param)
      print()
      print(accessToken[0:10] + '...')

      addUser(param, 'bearer ' + accessToken)

# Call Keycloak Add user api 
def addUser(param, token):
  headers = { 'Content-Type': 'application/json; charset=utf-8', 'Authorization': token }

  res = requests.post('http://localhost:8080/auth/admin/realms/{realm name}/users', data=json.dumps(param), headers=headers)

  print(res.status_code)
  print(res.text)

if __name__ == '__main__':
  makeBody()