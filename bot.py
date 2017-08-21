import logging
import os
import requests
import sqlite3
import telegram

import config
import modules

from math import atan2, cos, radians, sin, sqrt
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from time import sleep


# Setup logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        filename=os.path.dirname(os.path.realpath(__file__)) + "/logs/bot.log")
logger = logging.getLogger(__name__)

START_SENSORID, START_LIMIT = range(2)


def start(bot, update):
    # Check whether chat_id is already in database
    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id = ?", (int(update.message.chat_id),))
    fetched_users = c.fetchall()
    c.close()
    conn.close()

    if fetched_users != []:
        logger.info("User {user} called /start although he is already in the database".format(user=update.message.from_user.username))
        bot.send_message(chat_id=update.message.chat_id,
                         text="Du hast schon alles eingerichtet! Falls Du deine Daten bearbeiten möchtest, wähle /setsensorid oder /setlimit.")
        return ConversationHandler.END

    logger.info("User {user} called /start".format(user=update.message.from_user.username))
    bot.send_message(chat_id=update.message.chat_id,
                     text="Herzlich Willkommen bei [Luftdaten-Notification](https://github.com/Lanseuo/Luftdaten-Notification)!")
    bot.send_message(chat_id=update.message.chat_id,
                     text="Wie lautet deine Sensor-ID?")
    return START_SENSORID


def start_setsensorid(bot, update):
    sensor_id = update.message.text
    chat_id = update.message.chat_id

    # Check whether sensor_id is valid
    if modules.get_value(sensor_id) != False:

        # Check whether chat_id is already in database
        conn = sqlite3.connect(config.database_location)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE chat_id = ?", (int(chat_id),))
        fetched_users = c.fetchall()
        c.close()
        conn.close()

        # Save new user in db
        conn = sqlite3.connect(config.database_location)
        c = conn.cursor()
        c.execute("INSERT INTO users (sensor_id, chat_id, limitation, sent_message) VALUES (?, ?, ?, ?)",
                  (sensor_id, chat_id, "", "never"))
        conn.commit()
        c.close()
        conn.close()
        bot.send_message(chat_id=update.message.chat_id,
                         text="Deine Sensor-ID (" + sensor_id + ") wurde erfolgreich festgelegt!")
        logger.info("User {user} set sensor_id {sensor_id} with /start".format(user=update.message.from_user.username, sensor_id=sensor_id))

    else:
        logger.info("User {user} registered with wrong sensor_id {sensor_id}".format(user=update.message.from_user.username, sensor_id=sensor_id))
        bot.send_message(chat_id=update.message.chat_id,
                         text="Sensor " + sensor_id + " ist nicht verfügbar! Überprüfe deine Sensor ID und führe gebe die ID erneut ein!")
        return START_SENSORID

    bot.send_message(chat_id=update.message.chat_id,
                     text="Bei welchem Limit möchtest Du benachrichtigt werden?")
    return START_LIMIT


def start_setlimit(bot, update):
    limitation = update.message.text
    chat_id = update.message.chat_id

    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()
    c.execute("UPDATE users SET limitation = (?) WHERE chat_id = (?)", (limitation, chat_id))
    conn.commit()
    c.close()
    conn.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text="Dein Limit (" + limitation + "), bei dem Du benachrichtigt wirst, wurde erfolgreich geändert!")
    logger.info("User {user} set limit to {limit} with /start".format(user=update.message.from_user.username, limit=limitation))

    return ConversationHandler.END


def setsensorid(bot, update):
    try:
        sensor_id = update.message.text.split(" ")[1]
    except IndexError:
        # Only command given (no value)
        logger.info("User {user} called /setsensorid without value")
        bot.send_message(chat_id=update.message.chat_id,
                         text="Du musst einen Wert angeben! Beispiel: /setsensorid 000")
        return ConversationHandler.END

    chat_id = update.message.chat_id

    # Check whether sensor_id is valid
    if modules.get_value(sensor_id) != False:

        # Check whether chat_id is already in database
        conn = sqlite3.connect(config.database_location)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE chat_id = ?", (int(chat_id),))
        fetched_users = c.fetchall()
        c.close()
        conn.close()

        # User didn't already /start
        if fetched_users == []:
            logger.info("User {user} called /setsensorid not being in the database".format(user=update.message.from_user.username))
            bot.send_message(chat_id=update.message.chat_id, text="Richte mich erst einmal mit /start ein!")
            return ConversationHandler.END

        conn = sqlite3.connect(config.database_location)
        c = conn.cursor()
        c.execute("UPDATE users SET sensor_id = (?) WHERE chat_id = (?)", (sensor_id, chat_id))
        conn.commit()
        c.close()
        conn.close()
        bot.send_message(chat_id=update.message.chat_id,
                         text="Deine Sensor-ID (" + sensor_id + ") wurde erfolgreich verändert!")
        logger.info("User {user} updated sensor_id to {sensor_id} with /setsensorid".format(user=update.message.from_user.username,
                                                                          sensor_id=sensor_id))

    else:
        logger.info("User {user} registered with wrong sensor_id {sensor_id}".format(user=update.message.from_user.username, sensor_id=sensor_id))
        bot.send_message(chat_id=update.message.chat_id, text="Sensor " + sensor_id + " ist nicht verfügbar! Überprüfe deine Sensor ID und führe den Befehl erneut aus!")

    return ConversationHandler.END


def setlimit(bot, update):
    try:
        limitation = update.message.text.split(" ")[1]
    except IndexError:
        # Only command given (no value)
        logger.info("User {user} called /setlimit without value".format(user=update.message.from_user.username))
        bot.send_message(chat_id=update.message.chat_id,
                         text="Du musst einen Wert angeben! Beispiel: /setlimit 50")
        return ConversationHandler.END

    chat_id = update.message.chat_id

    # Check whether chat_id is already in database
    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE chat_id = ?", (int(chat_id),))
    fetched_users = c.fetchall()
    c.close()
    conn.close()

    if fetched_users == []:
        logger.info("User {user} called /setlimit not being in the database".format(user=update.message.from_user.username))
        bot.send_message(chat_id=update.message.chat_id, text="Richte mich erst einmal mit /start ein!")
        return ConversationHandler.END

    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()
    c.execute("UPDATE users SET limitation = (?) WHERE chat_id = (?)", (limitation, chat_id))
    conn.commit()
    c.close()
    conn.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text="Dein Limit (" + limitation + "), bei dem Du benachrichtigt wirst, wurde erfolgreich geändert!")
    logger.info("User {user} set limit to {limit} with /setlimit".format(user=update.message.from_user.username, limit=limitation))

    return ConversationHandler.END


def getvalue(bot, update):
    chat_id = update.message.chat_id

    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE chat_id = ?", (int(chat_id),))
    fetched_users = c.fetchall()
    c.close()
    conn.close()

    if fetched_users != []:
        sensor_id = fetched_users[0][1]
        value = modules.get_value(sensor_id)
        bot.send_message(chat_id=update.message.chat_id, text="Aktuell misst dein Feinstaub-Sensor *" + str(value) + " Partikel* pro m3.", parse_mode=telegram.ParseMode.MARKDOWN)
        logger.info("User {user} called /getvalue".format(user=update.message.from_user.username))

    else:
        logger.info("User {user} called /getvalue not being in the database".format(user=update.message.from_user.username))
        bot.send_message(chat_id=update.message.chat_id, text="Du musst mich zuerst mit /start einrichten!")

    return ConversationHandler.END


def details(bot, update):
    logger.info("User {user} asked for details".format(user=update.message.from_user.username))
    chat_id = update.message.chat_id
    conn = sqlite3.connect(config.database_location)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE chat_id = ?", (int(chat_id),))
    fetched_users = c.fetchall()
    c.close()
    conn.close()

    # User didn't already /start
    if fetched_users == []:
        logger.info(
            "User {user} called /setsensorid not being in the database".format(user=update.message.from_user.username))
        bot.send_message(chat_id=update.message.chat_id, text="Richte mich erst einmal mit /start ein!")
        return ConversationHandler.END

    user = fetched_users[0]
    value = modules.get_value(user[1])

    bot.send_message(chat_id=update.message.chat_id,
                     text="Sensor-ID: " + str(user[1]) + "\n" +
                     "Chat-ID: " + str(update.message.chat_id) + "\n" +
                     "Limit: " + str(user[3]) + "\n" +
                     "Messung: " + str(value) + " Partikel pro m3")
    return ConversationHandler.END


def location(bot, update):
    logger.info("User {user} sent location: {latitude} {longitude}".format(user=update.message.from_user.username,
                                                                           latitude=str(update.message.location["latitude"]),
                                                                           longitude=str(update.message.location["longitude"])))
    # Get position from message
    search_lat = update.message.location["latitude"]
    search_lon = update.message.location["longitude"]
    search_pos = (search_lat, search_lon)

    # Get location and id of sensors from API
    print(10*"1")
    r = requests.get("https://api.luftdaten.info/static/v2/data.dust.min.json")
    print(10*"2")
    sensors = r.json()

    # Get the sensor with the smallest distance to search_pos
    low_dist = float('inf')
    closest_sensor = None
    closest_sensor_pos = None
    for sensor in sensors:
        sensor_id = int(sensor["sensor"]["id"])
        sensor_pos = (float(sensor["location"]["latitude"]), float(sensor["location"]["longitude"]))

        # Calculate the distance between this sensor (i) and search_pos
        dist = sqrt(((search_pos[0] - sensor_pos[0]) ** 2) + ((search_pos[1] - sensor_pos[1]) ** 2))

        # If distance of this sensor (i) is smaller then the smallest, set new closest_sensor
        if dist < low_dist:
            low_dist = dist
            closest_sensor = sensor_id
            closest_sensor_pos = sensor_pos

    # Calculate distance between sensor_pos and closest_sensor
    lat1, lon1 = search_pos
    lat2, lon2 = closest_sensor_pos
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) * sin(dlat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = round(6371 * c)
    if distance < 1000:
        distance *= 1000
        distance = str(distance) + "m"
    elif distance >= 1000:
        distance = str(distance) + "km"

    # Send response to user
    bot.send_location(chat_id=update.message.chat_id, latitude=closest_sensor_pos[0], longitude=closest_sensor_pos[1])
    response = """
Nächste Sensor: {closest_sensor}
Entfernung: {distance}
Messung: {value} Partikel pro m3

Schicke mir /setsensorid {closest_sensor}, um ihn als deinen Hauptsensor festzulegen
    """.format(closest_sensor=str(closest_sensor), distance=distance, value=str(modules.get_value(closest_sensor)))
    bot.send_message(chat_id=update.message.chat_id,
                     text=response)

    return ConversationHandler.END


def help(bot, update):
    help_message = """
Ich schicke dir eine Nachricht, wenn der Feinstaubgehalt deines Sensors über ein bestimmtes Limit steigt.

Du hast folgende Möglichkeiten:

/start - Einrichtung starten
/setsensorid - Sensor-ID festlegen
/setlimit - Limit festlegen

/getvalue - aktueller Wert deines Sensors
/details - Details über deinen Sensor
    """
    logger.info("User {user} asked for help".format(user=update.message.from_user.username))
    bot.send_message(chat_id=update.message.chat_id, text=help_message)

    return ConversationHandler.END


def not_command(bot, update):
    logger.info("User {user} sent unknown command: {command}".format(user=update.message.from_user.username, command=update.message.text))
    bot.send_message(chat_id=update.message.chat_id,
                     text="Leider kenne ich diesen Befehl mit. Verwende /help um alle Befehle zu sehen.")
    return ConversationHandler.END


def cancel(bot, update):
    logger.info("User {user} canceled the conversation.".format(user=update.message.from_user.username))
    bot.send_message(chat_id=update.message.chat_id,
                     text="Abgebrochen ...")
    return ConversationHandler.END


def error_callback(bot, update, error):
    try:
        raise error
    except Exception as e:
        logger.error(str(e))


def main():
    logger.info("Started bot.py")

    updater = Updater(token=config.bottoken)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("getvalue", getvalue),
            CommandHandler("setsensorid", setsensorid),
            CommandHandler("setlimit", setlimit),
            CommandHandler("details", details),
            CommandHandler("help", help),
            MessageHandler(Filters.location, location),
        ],

        states={
            START_SENSORID: [MessageHandler(Filters.text, start_setsensorid)],
            START_LIMIT: [MessageHandler(Filters.text, start_setlimit)]
        },

        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error_callback)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    # Wait 10 seconds until network is available
    sleep(10)
    main()
