from paho.mqtt import client as mqtt_client
import random
import time
import requests
import json
import datetime
import configparser



class Config():
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.interval = int(config['DEFAULT']['interval'])
        self.sunriselength = int(config['DEFAULT']['sunriselength'])
        self.sunsetlength = int(config['DEFAULT']['sunsetlength'])
        self.maxbrightness = int(config['DEFAULT']['maxbrightness'])
        self.brightness100 = int(config['DEFAULT']['cloudbrightness100'])
        self.cloudbrightness100 = int(config['DEFAULT']['cloudbrightness100'])

        self.broker = config['MQTT']['broker']
        self.port = int(config['MQTT']['port'])   
        self.topic = config['MQTT']['topic3']
        self.brightnesscmd = config['MQTT']['brightnesscmd']
        self.username = config['MQTT']['username']
        self.password = config['MQTT']['password']
        self.clientId = f'python-mqtt-{random.randint(0, 1000)}'

        self.apikey = config['OWM']['apikey']
        self.lat = config['OWM']['lat']
        self.lon = config['OWM']['lon']
        self.url = str(config['OWM']['url']).format(self.lat,self.lon,yesterday,self.apikey)      
        
        
        
class Light():
    def __init__(self):
        self.nextaction = 0
        self.nextstepsunrise = 0
        self.sunrisenextstep = 0
        self.sunrisesecondsserstep = 0
        self.sunrisebrightness = 0
        self.nextstepsunset = 0
        self.sunsetnextstep = 0
        self.sunsetsecondsserstep = 0
        self.sunsetbrightness = 0
        self.maxbrightness = 0
        self.secondsperstep = 0
        self.sunriseaction = False
        self.sunsetaction = False
        

    def setNextAction(self, interval):
        currentTime = datetime.datetime.now()
        nxtAct = time.mktime(currentTime.timetuple())
        nxtAct += c.interval
        self.nextaction = nxtAct
        
        
    def setBrightnessFromWeather(self,sunact):
        # befindet wir uns nach sonnenaufgang und noch vordem sonnenuntergang 
        currentTime = datetime.datetime.now()
        if (self.nextaction < time.mktime(currentTime.timetuple())) and (not sunact):          
            response = requests.get(c.url)
            data = json.loads(response.text)
            print(str(data['current']['weather'][0]['main']) + ' - ' + str(data['current']['weather'][0]['description']))
            print('Wolkendichte: ' + str(data['current']['clouds']))
            brightness = int(c.maxbrightness - ((c.maxbrightness - c.cloudbrightness100)*(data['current']['clouds']/100)))
            print('angepasste Helligkeit: ' + str(brightness))
            publish(c.topic,'{'+c.brightnesscmd.format(brightness)+'}')
            self.setNextAction(c.interval)    


    def controlSunSet(self):
        currentTime = int(getTimeCodeMinusOneDay(datetime.datetime.now()))
        if not self.sunsetaction:
            if self.nextstepsunset == 0:            
                response = requests.get(c.url)
                data = json.loads(response.text)
                self.nextstepsunstep = data['current']['sunset']
                
                #print(self.nextstepsunstep)
                #print(time.mktime(currentTime.timetuple()))
                
            if self.nextstepsunset < currentTime:
                response = requests.get(c.url)
                data = json.loads(response.text)
                self.deltabrightness = int(c.maxbrightness - ((c.maxbrightness - c.cloudbrightness100)*(data['current']['clouds']/100)))          
                
                self.secondsperstep = c.sunsetlength / self.deltabrightness        
                self.nextstepsunset = currentTime + self.secondsperstep
                
                self.sunsetaction = True
            
        else:
            if self.nextstepsunset < currentTime:   
                if self.deltabrightness > 0:
                    self.nextstepsunset += self.secondsperstep
                    self.deltabrightness -= 1
                    print('Helligkeit Sonnenuntergang ' + str(self.deltabrightness))
                    publish(c.topic,'{'+c.brightnesscmd.format(str(self.deltabrightness))+'}')
                else:
                    self.nextstepsunset = getTimeCodeNextDayByHour(self.nextstepsunset,11)
                    print(self.nextstepsunset)
                    self.sunseteaction = False
                           

    def controlSunRise(self):
        currentTime = int(getTimeCodeMinusOneDay(datetime.datetime.now()))   
        
        if not self.sunriseaction:
            if self.nextstepsunrise == 0:            
                response = requests.get(c.url)
                data = json.loads(response.text)
                self.nextstepsunstep = data['current']['sunrise']
                
                #print(self.nextstepsunstep)
                #print(currentTime)
                
            if self.nextstepsunrise < currentTime:
                response = requests.get(c.url)
                data = json.loads(response.text)
                self.deltabrightness = 0
                self.maxbrightness = int(c.maxbrightness - ((c.maxbrightness - c.cloudbrightness100)*(data['current']['clouds']/100)))          
                
                self.secondsperstep = c.sunriselength / self.maxbrightness        
                self.nextstepsunrise = currentTime + self.secondsperstep
                
                self.sunriseaction = True
            
        else:
            if self.nextstepsunrise < currentTime:   
                if self.deltabrightness < self.maxbrightness:
                    self.nextstepsunrise += self.secondsperstep
                    self.deltabrightness += 1
                    print('Helligkeit Sonnenaufgang ' + str(self.deltabrightness))
                    publish(c.topic,'{'+c.brightnesscmd.format(str(self.deltabrightness))+'}')
                else:
                    self.nextstepsunrise = getTimeCodeNextDayByHour(self.nextstepsunrise,1)
                    print(self.nextstepsunrise)
                    self.sunriseaction = False
        
        
        
       
def getTimeCodeMinusOneDay(currentTime):
    day = currentTime.day - 1
    dateTime = datetime.datetime(currentTime.year,
                                 currentTime.month,
                                 day,
                                 currentTime.hour,
                                 currentTime.minute,
                                 currentTime.second)

    return time.mktime(dateTime.timetuple())


def getTimeCodeNextDayByHour(currentTime, hour):
    currentTimeStamp = datetime.datetime.fromtimestamp(currentTime)
    day = currentTimeStamp.day + 1
    minute = 0
    second = 0
    dateTime = datetime.datetime(currentTimeStamp.year,
                                 currentTimeStamp.month,
                                 day,
                                 hour,
                                 minute,
                                 second)

    return time.mktime(dateTime.timetuple())


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(c.clientId)
    client.username_pw_set(c.username, c.password)
    client.on_connect = on_connect
    client.connect(c.broker, c.port)
    return client


def publish(topic,value):
    client = connect_mqtt()
    client.publish(topic,str(value))
    client.disconnect()
    
    
    
if __name__ == '__main__':
    yesterdayInt = int(getTimeCodeMinusOneDay(datetime.datetime.now()))
    yesterday = str(yesterdayInt)
    print(yesterday)
    
    c = Config()
    l = Light()
    l.setNextAction(c.interval)
    
    while True:
        if l.sunriseaction or l.sunsetaction:
            sunControlled = True
        else:
            sunControlled = False
        #print(sunControlled)
        l.setBrightnessFromWeather(sunControlled);
        l.controlSunRise()
        l.controlSunSet()
        time.sleep(0.1)
        
