from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit


app = Flask(__name__)
socketio = SocketIO(app)


valuez =[ {
        'name': 'content',
        'informations': [
            {
                'type' : 'data',
                'name': 'Dzagob',
                'value': 20,
                'link-git': "https://github.com/Mark-Zagob/My-sample-project-01.git"
            }
        ]
    }]

@app.get("/")
def homepage():
    return "Hello, welcome to the homepage"

@app.get("/valuez")
def get_stores():
    return jsonify({'infor':valuez})

@app.put("/informations")
def update_information():
    data = request.get_json()
    for content in valuez:
        for info in content['informations']:
                info['type'] = data.get('type', info['type'])
                info['name'] = data.get('name', info['name'])
                info['value'] = data.get('value', info['value'])
                info['link-git'] = data.get('link-git', info['link-git'])
                socketio.emit('process_handler', {'informations': info})  # Emit event
                return jsonify({'message': 'Information updated successfully', 'informations': info})
    return jsonify({'message': 'Information not found'}), 404


@socketio.on('connect')
def connected():
    print("controller connected to application")
    
@socketio.on('disconnect')
def disconnected():
    print("disconnected")

#curl -X PUT -H "Content-Type: application/json" -d '{"value": 74}' http://192.168.100.61:32128/informations

# app.run(host='0.0.0.0',port=5000)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)