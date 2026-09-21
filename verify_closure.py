import urllib.request
import json

BASE_BACKEND = 'http://localhost:8000'
BASE_FRONTEND = 'http://localhost:3000'

accounts = [
    ('admin_tammy', 'Admin@123456', 'admin_hq'),
    ('farmer_ba_tam', 'Farmer@123456', 'farmer'),
    ('legacy_technician', 'Legacy@123456', 'technician'),
    ('packhouse_tammy', 'Packhouse@123456', 'packhouse_lead')
]

print('=== 1. VERIFYING CANONICAL USER ROLES & AUTH ===')
for username, password, expected_role in accounts:
    req = urllib.request.Request(
        f'{BASE_BACKEND}/api/v1/auth/login',
        data=json.dumps({'username_or_email': username, 'password': password}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        token = data['access_token']
    
    me_req = urllib.request.Request(
        f'{BASE_BACKEND}/api/v1/auth/me',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(me_req) as me_resp:
        me_data = json.loads(me_resp.read().decode())
        roles = me_data.get('roles', [])
        print(f'User: {username:20} -> roles: {roles} -> expected: {expected_role} -> PASS: {expected_role in roles}')

print('\n=== 2. FETCHING REAL POSTGRESQL ENTITY IDS ===')
# Get admin token for API queries
admin_req = urllib.request.Request(
    f'{BASE_BACKEND}/api/v1/auth/login',
    data=json.dumps({'username_or_email': 'admin_tammy', 'password': 'Admin@123456'}).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(admin_req) as resp:
    admin_token = json.loads(resp.read().decode())['access_token']

auth_headers = {'Authorization': f'Bearer {admin_token}'}

req_ga = urllib.request.Request(f'{BASE_BACKEND}/api/v1/growing-areas', headers=auth_headers)
with urllib.request.urlopen(req_ga) as r:
    gas = json.loads(r.read().decode())
    ga_id = gas[0]['id']
    ga_code = gas[0]['area_code']
    print(f'Real Growing Area ID: {ga_id} ({ga_code})')

req_farms = urllib.request.Request(f'{BASE_BACKEND}/api/v1/farms', headers=auth_headers)
with urllib.request.urlopen(req_farms) as r:
    farms = json.loads(r.read().decode())
    farm_id = farms[0]['id']
    farm_code = farms[0]['farm_code']
    print(f'Real Farm ID: {farm_id} ({farm_code})')

req_plots = urllib.request.Request(f'{BASE_BACKEND}/api/v1/plots', headers=auth_headers)
with urllib.request.urlopen(req_plots) as r:
    plots = json.loads(r.read().decode())
    plot_id = plots[0]['id']
    plot_code = plots[0]['plot_code']
    print(f'Real Plot ID: {plot_id} ({plot_code})')

print('\n=== 3. VERIFYING DYNAMIC FRONTEND ROUTES WITH REAL IDS ===')
routes = [
    '/',
    '/farmers',
    '/growing-areas',
    f'/growing-areas/{ga_id}',
    '/farms',
    f'/farms/{farm_id}',
    f'/plots/{plot_id}',
    '/map'
]

all_passed = True
for route in routes:
    url = f'{BASE_FRONTEND}{route}'
    try:
        with urllib.request.urlopen(url) as resp:
            print(f'Route: {route:45} -> Status: {resp.status} OK')
    except Exception as e:
        print(f'Route: {route:45} -> FAIL: {e}')
        all_passed = False

if all_passed:
    print('\n>>> ALL DYNAMIC REAL ID ROUTES RENDERED WITH HTTP 200 OK! <<<')
