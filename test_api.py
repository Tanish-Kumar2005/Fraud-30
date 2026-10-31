import urllib.request, json

BASE = 'http://127.0.0.1:5000'

def post(path, data):
    try:
        req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except Exception as e:
        return None, str(e)

def get(path):
    try:
        r = urllib.request.urlopen(BASE + path)
        return r.status, json.loads(r.read())
    except Exception as e:
        return None, str(e)

# Test register
s, d = post('/api/auth/register', {'email': 'test@soc.gov', 'password': 'test123', 'analyst_name': 'Test Analyst', 'soc_tier': 'SOC Tier-1'})
print('Register:', s, str(d)[:80])

# Test login
s, d = post('/api/auth/login', {'email': 'test@soc.gov', 'password': 'test123'})
print('Login:', s, str(d)[:80])

# Test text analysis - scam
s, d = post('/api/analyse/text', {'transcript': 'Hello, this is Officer Rajesh from CBI. Digital arrest warrant issued. Transfer funds immediately.'})
print('Scam text:', s, 'scam=' + str(d.get('is_scam', 'N/A')) + ' risk=' + str(d.get('risk_score', 'N/A')))

# Test text analysis - safe
s, d = post('/api/analyse/text', {'transcript': 'Hello, I am calling from your bank. Your monthly statement is available online.'})
print('Safe text:', s, 'scam=' + str(d.get('is_scam', 'N/A')) + ' risk=' + str(d.get('risk_score', 'N/A')))

# Test get alerts
s, d = get('/api/alerts')
print('Alerts:', s, 'total=' + str(d.get('stats', {}).get('totalAlerts', 'N/A')))

print('All API tests completed!')