import logging
import os
from dotenv import load_dotenv
import datetime
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import api
import time
import threading
from priveleges import check_priveleges

import configparser

district_config = configparser.ConfigParser()
group_config    = configparser.ConfigParser()



logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


logger = logging.getLogger('telegram_bot.info')

def get_district_ids(name):
    district_config.read('configs/district_code.ini')
    try:
        return district_config['DISTRICTS'][name.lower()]
    except Exception as e:
        logger.error(e)
        return None
    
def get_group_ids():
    group_config.read('configs/group_district_map.ini')
    try:
        return dict(group_config['GROUPS'])
    except Exception as e:
        logger.log(e)
        return None

def shutdown():
    updater.stop()
    updater.is_idle = False

@check_priveleges
def stop(bot,update, context):
    if context.args[0]=="AlphaBeta123":
        threading.Thread(target=shutdown).start()
    else:
        update.message.reply_text("Incorrect Password.")
def start(update, context):
    # userdb.store_user(update.message.chat.username,update.message.chat.id)
    update.message.reply_text(os.getenv("HELLO_TEXT"))

def error(update, context):
    print("Update caused error ",context.error)
    logger.warning("Update caused error %s",  context.error)

def update_message(update, context):
    update.message.reply_text("New Vaccine Doses have come for some Districts")


@check_priveleges
def APIStatus(update, context):
    while True:
        res = api.fetch_values(307)
        if res == "CoWin API Down\n":
            echo_v1(update, context, custom_message="CoWin API Down\n")
            time.sleep(600)
        else:
            echo_v1(update,context, custom_message="CoWin API Up and Running!\n")
            break

@check_priveleges
def fetch_district_code(update, content):
    try:
        echo(update, content, content.args[0])
    except Exception as e:
        logger.error(e)


@check_priveleges
def stopNotify(update, context):
    try:
        update.message.reply_text("Stopping Notification!")
    except Exception as e:
        logger.error(e)

@check_priveleges
def notify(update,content):
    t1 = datetime.datetime.now()

    group_ids = get_group_ids()
    if update.message.chat.id not in group_ids:
        group_ids[update.message.chat.id] = get_district_ids(content.args[0])
    
    if group_ids[update.message.chat.id]==None:
        api_ = os.getenv("TELEGRAM_API")+os.getenv("TOKEN")+'/sendMessage?chat_id='+str(update.message.chat.id)+'&text= District Not Found in our List. Is the spelling correct?'
        response = requests.get(api_)
        logger.log(response.content.decode('utf8'))
        print(response.content.decode('utf8'))        
        return 0
    
    check_time = 10
    downtime_count = 0
    while True:
        t2 = datetime.datetime.now()-t1
       
        if t2.seconds>check_time:
            downtime_flag=False
            for group_id in group_ids:
                logger.error(t2)
                res = api.fetch_values(group_ids.get(group_id,None))
                if res in "Vaccine Unavailable.\n":
                    time.sleep(300)

                elif res in "CoWin API Down\n":
                    logger.error("CoWin API Down\n")
                    if downtime_count==0:
                        api_ = os.getenv("TELEGRAM_API")+os.getenv("TOKEN")+'/sendMessage?chat_id='+str(group_id)+'&text=CoWin API is down!'
                        response = requests.get(api_)
                        print(response.content.decode('utf8'))
                    downtime_flag = True
                    time.sleep(600)
                else:
                    api_ = os.getenv("TELEGRAM_API")+os.getenv("TOKEN")+'/sendMessage?chat_id='+str(group_id)+'&text='+res
                    response = requests.get(api_)
                    print(response.content.decode('utf8'))
                    check_time=60
                
                t1 = datetime.datetime.now()
            if downtime_flag:
                downtime_count+=1
        
        if downtime_count==6:
            for group_id in group_ids:
                api_ = os.getenv("TELEGRAM_API")+os.getenv("TOKEN")+'/sendMessage?chat_id='+str(group_id)+'&text= CoWin API Down - Turning Off Notifier'
                response = requests.get(api_)
                print(response.content.decode('utf8'))
            break


@check_priveleges
def district(update, context):
    # print(update)
    print(get_district_ids(context.args[0].lower()))
    echo(update, context, get_district_ids(context.args[0].lower()))
    
@check_priveleges
def echo(update, context, district_code=None):
    if district_code==None:
        district_code = get_district_ids(context.args[0].lower())
    
    if(district_code):
        # update.message.reply_text("The District Code is: "+str(district_code))
        lis = api.fetch_values(district_code)
        # print(lis)
        if lis:
            update.message.reply_text(lis)
        else:
            print(lis)
    else:
        update.message.reply_text("District Not Found! Make sure the spelling is correct!")

def echo_v1(update, context, custom_message=None):
    try:
        if custom_message:
            update.message.reply_text(custom_message)
        else:
            update.message.reply_text("I don't know how to reply to that! :)")
    except Exception as e:
        print(e)

@check_priveleges
def broadcast(update, context):
    user_list = userdb.fetch_users()
    for users in user_list:
        api_ = os.getenv("TELEGRAM_API")+os.getenv("TOKEN")+'/sendMessage?chat_id='+str(users[1])+'&text='+os.getenv('BROADCAST_MSG')
        response = requests.get(api_)
        print(response.content.decode('utf8'))



load_dotenv()
updater = Updater(os.getenv("TOKEN"), use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
# dp.add_handler(CommandHandler("list", userdb.list_users))
dp.add_handler(CommandHandler("district", district, pass_args=True))
dp.add_handler(CommandHandler("districtcode", fetch_district_code, pass_args=True))
dp.add_handler(CommandHandler('stopNotify', stopNotify))
dp.add_handler(CommandHandler("broadcast", broadcast))
dp.add_handler(CommandHandler('stop', stop, pass_args=True))
dp.add_handler(CommandHandler("notify", notify, pass_args=True))
dp.add_handler(CommandHandler("APIStatus", APIStatus))
dp.add_handler(MessageHandler(Filters.text, echo_v1))

dp.add_error_handler(error)

updater.start_polling()
updater.idle()