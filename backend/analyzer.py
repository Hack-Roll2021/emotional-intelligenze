import os
import cv2
import requests
import pprint
from PIL import Image, ImageDraw
import time
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person

AZURE_KEY = os.getenv("AZURE_KEY_1")

endpoint = "https://southeastasia.api.cognitive.microsoft.com/face/v1.0/detect"

# API Call Config
headers = {'Ocp-Apim-Subscription-Key': AZURE_KEY, 'Content-Type': 'application/octet-stream'}
params = {
    'returnFaceAttributes': 'emotion',
    'returnFaceId': 'true',
    'detectionModel': 'detection_01'
}

# Convert width height to a point in a rectangle
def getRectangle(faceDictionary):
    # print(faceDictionary)
    rect = faceDictionary["faceRectangle"]
    left = rect["left"]
    top = rect["top"]
    right = left + rect["width"]
    bottom = top + rect["height"]
    
    return ((left, top), (right, bottom))

def analyze_video(url):
    counter = 0
    # Opens the Video file
    cap = cv2.VideoCapture(url)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # store the emotions of people in the video
    res = []
    i = 1
    is_first_frame = True
    first_frame_faces = []
    result = {}
    face_client = FaceClient("https://instance-01.cognitiveservices.azure.com/", CognitiveServicesCredentials(AZURE_KEY))
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # process frames every 4 seconds
        # make sure we don't bust azure's free tier
        if i % (4*fps) == 0:
            # to write frames to disk
            # cv2.imwrite('test_' + str(i) + '.jpg', frame)
            ret, buf = cv2.imencode('.jpg', frame)
            cv2.imwrite('data\pic.jpg', frame)
            # Azure API Call
            if is_first_frame:
                response = requests.post(endpoint, headers=headers, params=params, data=buf.tobytes())
                # counter += 1
                # if counter > 20: 
                #     time.sleep(20)
                #     counter = 0
                response.raise_for_status()
                output = response.json()

                # Download the image from the url
                # response = requests.get('/data/pic.jpg')
                # img = Image.open(BytesIO(response.content))
                img = Image.open("data\pic.jpg")

                # For each face returned use the face rectangle and draw a red box.
                # print('Drawing rectangle around face... see popup for results.')
                draw = ImageDraw.Draw(img)
                for face in output:
                    draw.text((face["faceRectangle"]["left"], face["faceRectangle"]["top"]), face["faceId"], align ="left", fill="pink") 
                    draw.rectangle(getRectangle(face), outline='yellow') 

                # Display the image in the users default image browser.
                img.show()

                first_frame_faces = list(map(lambda x: x["faceId"], output))
                for x in first_frame_faces:
                    curr_result = {}
                    for y in output:
                        if y["faceId"] == x:
                            curr_result = y
                            break
                    result[x] = []
                    result[x].append(curr_result["faceAttributes"]["emotion"])
                is_first_frame = False
            else:
                response = requests.post(endpoint, headers=headers, params=params, data=buf.tobytes())
                counter += 1
                if counter > 20: 
                    time.sleep(20)
                    counter = 0
                response.raise_for_status()
                output = response.json()
                curr_frame_faces = list(map(lambda x: x["faceId"], output))
                similar_faces = False
                for x in first_frame_faces:
                    similar_faces = face_client.face.find_similar(face_id=x, face_ids=curr_frame_faces)
                    counter += 1
                    if counter > 20: 
                        print('sleeping')
                        time.sleep(20) 
                        counter = 0
                    confidence = 0
                    face_id = "null"
                    for face in similar_faces:
                        if face.confidence > confidence:
                            face_id = face.face_id
                    if face_id != "null":
                        for y in output:
                            if y["faceId"] == face_id:
                                result[x].append(y["faceAttributes"]["emotion"])
                                break
        i += 1

    # print("")
    # pp = pprint.PrettyPrinter(indent=1)
    # pp.pprint(result)
    cap.release()
    cv2.destroyAllWindows()
    return result

