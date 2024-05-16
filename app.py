from tinydb import TinyDB
from flask import Flask, render_template, request, jsonify, make_response
from flask_jwt_extended import (
    JWTManager, create_access_token,
    get_jwt_identity, jwt_required,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, create_refresh_token,

)
from config import CLIENT_ID, REDIRECT_URI
from controller import Oauth
from model import UserData, UserModel


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = "546"
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 30
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 100
jwt = JWTManager(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/oauth")
def oauth_api():
    """
    # OAuth API [GET]
    사용자로부터 authorization code를 인자로 받은 후,
    아래의 과정 수행함
    1. 전달받은 authorization code를 통해서
        access_token, refresh_token을 발급.
    2. access_token을 이용해서, Kakao에서 사용자 식별 정보 획득
    3. 해당 식별 정보를 서비스 DB에 저장 (회원가입)
    3-1. 만약 이미 있을 경우, (3) 과정 스킵
    4. 사용자 식별 id를 바탕으로 서비스 전용 access_token 생성
    """
    code = str(request.args.get('code'))

    oauth = Oauth()
    auth_info = oauth.auth(code)
    user = oauth.userinfo("Bearer " + auth_info['access_token'])

    user = UserData(user)
    UserModel().upsert_user(user)

    resp = make_response(render_template('address.html'))
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    resp.set_cookie("logined", "true")
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)

    return resp

@app.route('/token/refresh')
@jwt_required(refresh=True)
def token_refresh_api():
    """
    Refresh Token을 이용한 Access Token 재발급
    """
    user_id = get_jwt_identity()
    resp = jsonify({'result': True})
    access_token = create_access_token(identity=user_id)
    set_access_cookies(resp, access_token)
    return resp


@app.route('/token/remove')
def token_remove_api():
    """
    Cookie에 등록된 Token 제거
    """
    resp = jsonify({'result': True})
    unset_jwt_cookies(resp)
    resp.delete_cookie('logined')
    return resp

@app.route('/oauth/url')
def oauth_url_api():
    """
    Kakao OAuth URL 가져오기
    """
    return jsonify(
        kakao_oauth_url="https://kauth.kakao.com/oauth/authorize?client_id=%s&redirect_uri=%s&response_type=code" \
        % (CLIENT_ID, REDIRECT_URI)
    )

@app.route("/userinfo")
@jwt_required()
def userinfo():
    """
    Access Token을 이용한 DB에 저장된 사용자 정보 가져오기
    """
    user_id = get_jwt_identity()
    userinfo = UserModel().get_user(user_id).serialize()
    return jsonify(userinfo)



@app.route("/oauth/refresh", methods=['POST'])
def oauth_refesh_api():
    """
    # OAuth Refresh API
    refresh token을 인자로 받은 후,
    kakao에서 access_token 및 refresh_token을 재발급.
    (% refresh token의 경우,
    유효기간이 1달 이상일 경우 결과에서 제외됨)
    """
    refresh_token = request.get_json()['refresh_token']
    result = Oauth().refresh(refresh_token)
    return jsonify(result)

@app.route("/oauth/userinfo", methods=['POST'])
def oauth_userinfo_api():
    """
    # OAuth Userinfo API
    kakao access token을 인자로 받은 후,
    kakao에서 해당 유저의 실제 Userinfo를 가져옴
    """
    access_token = request.get_json()['access_token']
    result = Oauth().userinfo("Bearer " + access_token)
    return jsonify(result)

selected_ingredients = []  # 선택된 재료를 저장할 전역 변수

@app.route('/receive-ingredients', methods=['GET','POST'])
def receive_ingredients():
    global selected_ingredients
    data = request.json  # JSON 형식으로 전송된 데이터 받기
    selected_ingredients = data.get('ingredients', [])  # 재료 목록 가져오기
    return jsonify({'message': 'Selected ingredients received successfully.'})


@app.route('/receive-address', methods=['GET','POST'])
def receive_address():
    global city
    global county
    global detail_address
    data = request.json  # JSON 형식으로 전송된 데이터 받기
    city = data.get('city', [])
    county = data.get('county', [])
    detail_address = data.get('detail_address', [])
    return jsonify({'message': 'address received successfully.'})


@app.route('/index/delivery')
def delivery():
    global city
    global county
    global detail_address
    # 배달 정보를 delivery.html에 전달하여 렌더링
    return render_template('delivery.html', city=city, county=county, detail_address=detail_address)

@app.route('/send_address_deliver', methods=['GET','POST'])
def send_address_deliver():
    # POST 요청으로부터 도시와 군/구 정보를 받아옴
    selected_city = request.form['city']
    selected_county = request.form['county']
    # 받아온 정보를 데이터베이스에 저장
    data = {'city': selected_city, 'county': selected_county}
    db = TinyDB('db.json')
    db.insert(data)
    # index.html을 렌더링하여 반환
    return render_template('index.html')


@app.route('/index/delivery/send_price')
def price():
    global selected_ingredients
    # 선택된 재료와  send_price.html에 전달하여 렌더링
    return render_template('send_price.html', ingredients=selected_ingredients)


if __name__ == '__main__':
    app.run(debug=True)