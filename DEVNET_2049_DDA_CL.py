
# developed by Gabi Zapodeanu, TSA, GSS, Cisco Systems

# !/usr/bin/env python3

import requests
import json
import time
import requests.packages.urllib3
import os
import os.path

from requests_toolbelt import MultipartEncoder  # required to encode messages uploaded to Spark
from PIL import Image, ImageDraw, ImageFont
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth  # for Basic Auth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # Disable insecure https warnings

# Replace these params with your lab info

EM_URL = 'https://172.16.11.30/api/v1'  # https://DDA_apic_em
EM_USER = 'python'
EM_PASSW = 'Clive.17'

CMX_URL = 'https://172.16.11.27/'
CMX_USER = 'python'
CMX_PASSW = 'Clive!17'
CMX_AUTH = HTTPBasicAuth(CMX_USER, CMX_PASSW)

SPARK_URL = 'https://api.ciscospark.com/v1'
SPARK_AUTH = 'Bearer ' + 'OTkyMTU2NGUtYjkzZi00OTQ3LTlj.....'
ROOM_NAME = 'MDE Line Outage'
IT_ENG_EMAIL = 'gabriel.zapodeanu@gmail.com'
OT_ENG_EMAIL = '...@...'

TROPO_KEY = '58456f49686444754646556a694f55624d4....'

PI_URL = 'https://172.16.11.25'
PI_USER = 'python'
PI_PASSW = 'Clive.17'
PI_AUTH = HTTPBasicAuth(PI_USER, PI_PASSW)

AGV_DICT = {'70:ec:e4:74:f7:d4': 5, '78:a3:e4:f1:de:f2': 10}  # sample lab AGV list
MDE_SSID = 'CLIVE'
HMI = '172.16.11.2'

LINE = '______________________________________\n'



def pprint(json_data):
    """
    Pretty print JSON formatted data
    :param json_data:
    :return:
    """

    print(json.dumps(json_data, indent=4, separators=(' , ', ' : ')))


def mde_initial_info():
    """
    This function will print the initial information about the AGV's:
    - number of AGV's
    - the dictionary  that includes the AGV's MAC addresses and the cart number
    - the list with all AGV's MAC addresses
    :param : global Dictionary AGV_DICT with the AGV database
    :return: the list of all AGV MAC addresses
    """

    print('\n')
    print(LINE)
    print('Number of AGVs: ', len(AGV_DICT))
    pprint(AGV_DICT)
    agv_mac_list = []
    for agvs in AGV_DICT:
        agv_mac_list.append(agvs)
    print('AGV MAC List: ', agv_mac_list)
    return agv_mac_list


def all_client_number():
    """
    This function will find out how many wireless clients are visible in the environment
    REST API call to CMX - /api/location/v2/clients/count
    :param
    :return: The total number of clients, associated and not associated with the MDE SSID
    """

    url = CMX_URL + 'api/location/v2/clients/count'
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, auth=CMX_AUTH, verify=False)
    response_json = response.json()
    clients_number = response_json['count']
    print('\nNumber of clients: ', clients_number)
    return clients_number


def check_cmx_connected_clients():
    """
    This function will connect to CMX to find out:
    - the total number of clients
    - the total number of clients associated to the MDE SSID
    - will create a list for all associated clients
    - each list element is a dictionary that includes:
        - the MAC address, IP address, x/y coordinates on the map
        - the MAC address of the AP connected to client
    REST API call to CMX - /api/location/v2/clients
    :param
    :return: list of dictionaries. Each item in the list is a dictionary with the above client information
    """

    url = CMX_URL + 'api/location/v2/clients'
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, auth=CMX_AUTH, verify=False)
    response_json = response.json()
    client_list = []
    for dicts in response_json:
        ssid = dicts.get('ssId')
        if ssid == MDE_SSID:
            client_info = {}
            client_info = {'client_mac': (dicts['macAddress']),
                           'ip_address': (dicts['ipAddress'][0]),
                           'ap_mac': (dicts['apMacAddress']),
                           'x': (dicts['mapCoordinate']['y']),
                           'y': (dicts['mapCoordinate']['y']),
                           'band': (dicts['band'])}
            client_list.append(client_info)
    print('Number of AGVs associated ', len(client_list))
    return client_list


def get_cmx_map(campus, building, floor, file):
    """
    The function will get the floor map for the floor with the name {floor},
    located in the specified building and campus.
    REST API call to CMX - 'api/config/v1/maps/image/' + campus/building/floor
    :param campus: campus name
    :param building: building name
    :param floor: floor name
    :param file: file name to save the image to
    :return: save the floor map image
    """

    url = CMX_URL + 'api/config/v1/maps/image/' + campus + '/' + building + '/' + floor
    header = {'content-type': 'application/json'}
    response = requests.get(url, headers=header, auth=CMX_AUTH, verify=False)

    # open a file to save the image to

    image_file = open(file, 'wb')
    image_file.write(response.content)  # save the content of the request as it comes back as an image and not JSON
    image_file.close()


def get_cmx_ap_info(campus, building, floor, ap_name):
    """
    The function will get the x/y coordinates of the AP with the name {ap_name} located on
    the floor with the name {floor}, located in the specified building and campus
    :param campus: campus name
    :param building: building name
    :param floor: floor name
    :param ap_name: AP name
    :return: x/y coordinates, from the top left corner of the image
    """

    url = CMX_URL + 'api/config/v1/maps/info/' + campus + '/' + building + '/' + floor
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, auth=CMX_AUTH, verify=False)
    aps_list = response.json()['accessPoints']
    for ap in aps_list:
        if ap['name'] == ap_name:
            ap_x = ap['mapCoordinates']['x']
            ap_y = ap['mapCoordinates']['y']
    return ap_x, ap_y


def check_missing_agv(agv_mac_list):
    """
    This function will loop to check every 10 seconds if we lost connectivity to AGV's
    It will require an input with the AGV's MAC addresses
    It will update a list which includes this info for all associated clients
        - each list element is a dictionary that includes:
        - the MAC address, IP address, x/y coordinates on the map
        - the MAC address of the AP previously connected to client
    The function will update the database if the current status of clients.
    :param agv_mac_list: list of all AGV MAC addresses
    :return: Missing AGV info - MAC address, IP Address, x/y coordinates
             and the MAC address of the last AP connected to client
    """

    clients_list = check_cmx_connected_clients()
    normal_op = True
    while normal_op:
        clients_list_new = check_cmx_connected_clients()
        agv_connected_mac_list = []
        for items in clients_list_new:
            agv_connected_mac_list.append(items['client_mac'])
        print('AGV Connected MAC List: ', agv_connected_mac_list)
        if set(agv_mac_list) != set(agv_connected_mac_list):
            normal_op = False
        else:
            time.sleep(6)  # required to pace the requests to CMX APIs
            clients_list = clients_list_new[:]  # update the client list with the most recent information
    missing_agv = []
    for agvs in agv_mac_list:
        if agvs not in agv_connected_mac_list:
            missing_agv.append(agvs)
    print('Missing AGV MAC address is: ', missing_agv)
    print('Missing AGV number is: ', AGV_DICT[missing_agv[0]])
    missing_agv_info = {}
    for dicts in clients_list:
        mac_add = dicts.get('client_mac')
        if missing_agv[0] == mac_add:
            missing_agv_info = dicts
    print('Missing AGV info is: ')
    pprint(missing_agv_info)
    return missing_agv_info


def create_spark_room(room_name):
    """
    This function will create a Spark room.
    API call to Spark - '/rooms'
    :param room_name: The new room title
    :return: Spark room id
    """

    payload = {'title': room_name}
    url = SPARK_URL + '/rooms'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    room_response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    room_json = room_response.json()
    room_number = room_json['id']
    print('Created Room with the name:  ', ROOM_NAME)
    return room_number


def add_membership(room_id, email_invite):
    """
    This function will add membership to the room with the room id
    API call to Spark - '/memberships'
    :param room_id: Spark room id
    :param email_invite: Spark member email to invite to join the room
    :return:
    """

    payload = {'roomId': room_id, 'personEmail': email_invite, 'isModerator': 'true'}
    url = SPARK_URL + '/memberships'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    print("Invitation sent to:  ", email_invite)


def post_message(room_id, message):
    """
    This function will post a message in a Spark room
    APIC call to Spark - '/messages'
    :param room_id: Spark room id
    :param message: Text message to be posted
    :return:
    """

    payload = {'roomId': room_id, 'text': message}
    url = SPARK_URL + '/messages'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    print("Message posted:  ", message)


def post_spark_room_file(room_id, file_name, file_type, file_path):
    """
    This function will post the file with the name {file_name}, type of file {file_type}, 
    from the local machine folder with the path {file_path}, to the Spark room with the id {room_id}
    Followed by API call /messages
    :param room_id: Spark room id
    :param file_name: File name to be uploaded
    :param file_type: File type
    :param file_path: File path local on the computer
    :return: 
    """

    # get the file name without the extension
    file = file_name.split('.')[0]

    payload = {'roomId': room_id,
               'files': (file, open(file_path+file_name, 'rb'), file_type)
               }
    # encode the file info, example: https://developer.ciscospark.com/blog/blog-details-8129.html

    m = MultipartEncoder(fields=payload)
    url = SPARK_URL + '/messages'
    header = {'content-type': m.content_type, 'authorization': SPARK_AUTH}
    requests.post(url, data=m, headers=header, verify=False)

    print('File posted :  ', file_path+file_name)


def delete_room(room_id):
    """
    This function will delete a Spark room
    API call to Spark + '/rooms'
    :param room_id: Spark room id
    :return:
    """

    url = SPARK_URL + '/rooms/' + room_id
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.delete(url, headers=header, verify=False)
    print("Deleted Spark Room:  ", ROOM_NAME)


def get_service_ticket():
    """
    This function will generate a ticket to access APIC-EM
    API call to APIC-Em + '/ticket'
    :return: APIC-EM ticket
    """

    payload = {'username': EM_USER, 'password': EM_PASSW}
    url = EM_URL + '/ticket'
    header = {'content-type': 'application/json'}
    ticket_response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    if not ticket_response:
        print('No data returned!')
    else:
        ticket_json = ticket_response.json()
        ticket = ticket_json['response']['serviceTicket']
        print('APIC-EM ticket: ', ticket)
        return ticket


def get_device_id(device_name, ticket):
    """
    This function will find the APIC-EM device id for the device with the name {device_name}
    :param device_name: device hostname
    :param ticket: APIC-EM ticket
    :return: APIC-EM device id
    """

    url = EM_URL + '/network-device/'
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    device_response = requests.get(url, headers=header, verify=False)
    device_json = device_response.json()
    device_list = device_json['response']
    for device in device_list:
        if device['hostname'] == device_name:
            device_id = device['id']
    return device_id


def check_ap_status(mac_add, ticket):

    """
    This function will check the status of the AP last connected to the disconnected AGV.
    REST API call to APIC-EM + '/network-device/'
    :param mac_add: the AP MAC address
    :param ticket: APIc_ME auth ticket
    :return: The AP APIC-EM id, name, reachability status
    """

    url = EM_URL + '/network-device'
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    response = requests.get(url, headers=header, verify=False)
    device_json = response.json()
    device_list = device_json['response']
    ap_status = 'Unreachable'
    for items in device_list:
        if items['macAddress'] == mac_add:
            ap_reach = items['reachabilityStatus']
            ap_id = items['id']
            ap_name = items['hostname']
    return ap_id, ap_name, ap_reach


def check_switch_status(ap_id, ticket):
    """
    This function will check the status of the Access Switch connected to the AP
    REST API call to APIC-EM + '/topology/physical-topology'
    :param ap_id: APIC-EM AP id
    :param ticket: APIC-EM auth ticket
    :return: The Access Switch name, management IP address, reachability, switchport, switchport_status
    """

    links_list = []
    url = EM_URL + '/topology/physical-topology'
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    response = requests.get(url, headers=header, verify=False)
    topology_json = response.json()
    links_list = topology_json['response']['links']
    for items in links_list:
        if items['source'] == ap_id:
            if 'endPortName' in items:    # required to identify which link dict has the info
                switch_id = items['target']
                switchport = items['endPortName']
    url = EM_URL + '/network-device/' + switch_id
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    response = requests.get(url, headers=header, verify=False)
    device_json = response.json()['response']
    switch_name = device_json['hostname']
    switch_mngmnt = device_json['managementIpAddress']
    switch_reachability = device_json['reachabilityStatus']
    url = EM_URL + '/interface/network-device/' + switch_id + '/interface-name'
    payload = {'deviceId': switch_id, 'name': switchport}
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    response = requests.get(url, params=payload, headers=header, verify=False)
    switchport_json = response.json()
    switchport_status = switchport_json['response']['status']
    return switch_name, switch_mngmnt, switch_reachability, switchport, switchport_status


def sync_device(device_name, ticket):
    """
    This function will sync the device configuration from the device with the name {device_name}
    :param device_name: device hostname
    :param ticket: APIC-EM ticket
    :return: the response, 202 if sync initiated
    """

    device_id = get_device_id(device_name, ticket)
    param = [device_id]
    url = EM_URL + '/network-device/sync'
    header = {'accept': 'application/json', 'content-type': 'application/json', 'X-Auth-Token': ticket}
    sync_response = requests.put(url, data=json.dumps(param), headers=header, verify=False)
    return sync_response.status_code


def create_path_visualisation(src_ip, dest_ip, ticket):
    """
    This function will create a new Path Visualisation between the source IP address {src_ip} and the
    destination IP address {dest_ip}
    :param src_ip: Source IP address
    :param dest_ip: Destination IP address
    :param ticket: APIC-EM ticket
    :return: APIC-EM path visualisation id
    """

    param = {
        'destIP': dest_ip,
        'periodicRefresh': False,
        'sourceIP': src_ip
    }

    url = EM_URL + '/flow-analysis'
    header = {'accept': 'application/json', 'content-type': 'application/json', 'X-Auth-Token': ticket}
    path_response = requests.post(url, data=json.dumps(param), headers=header, verify=False)
    path_json = path_response.json()
    path_id = path_json['response']['flowAnalysisId']
    return path_id


def get_path_visualisation_info(path_id, ticket):
    """
    This function will return the path visualisation details for the APIC-EM path visualisation {id}
    :param path_id: APIC-EM path visualisation id
    :param ticket: APIC-EM ticket
    :return: Path visualisation details in a list [device,interface_out,interface_in,device...]
    """

    url = EM_URL + '/flow-analysis/' + path_id
    header = {'accept': 'application/json', 'content-type': 'application/json', 'X-Auth-Token': ticket}
    path_response = requests.get(url, headers=header, verify=False)
    path_json = path_response.json()
    path_info = path_json['response']
    path_status = path_info['request']['status']
    path_list = []
    if path_status == 'COMPLETED':
        network_info = path_info['networkElementsInfo']
        path_list.append(path_info['request']['sourceIP'])
        for elem in network_info:
            try:
                path_list.append(elem['ingressInterface']['physicalInterface']['name'])
            except:
                pass
            try:
                path_list.append(elem['name'])
            except:
                pass
            try:
                path_list.append(elem['egressInterface']['physicalInterface']['name'])
            except:
                pass
        path_list.append(path_info['request']['destIP'])
    return path_status, path_list


def tropo_notification():

    """
    This function will call Tropo for a voice notification
    The MDENotification.py script is hosted by Tropo:
    -----
    call ("+15033094949")
    say ("Urgent! MDE Line Outage! Check Spark Room for details")
    -----
    We will send a get request to launch this script that will call my cell phone
    and Tropo voice will read the message.
    """

    url = 'https://api.tropo.com/1.0/sessions?action=create&token=' + TROPO_KEY
    header = {'accept': 'application/json'}
    response = requests.get(url, headers=header, verify=False)
    response_json = response.json()
    result = response_json['success']
    if result:
        notification = 'successful'
    else:
        notification = 'not successful'
    print('Tropo notification: ', notification)
    return notification


def image_process_annotate(in_image, out_image, text, color, font_size, x, y):
    """
    The function will annotate an image {in_image}. The {text} will be marked on the image with the {color} at
    coordinates {x,y}
    :param in_image: source image file
    :param out_image: destination image file
    :param text: the annotation text
    :param font_size: text font size
    :param color: color
    :param x: x coordinate
    :param y: y coordinate
    :return: It will save the annotated image with the name {out_image}
    """

    image = Image.open(in_image)  # open image file
    image_width, image_height = image.size  # size of the floor
    print('Floor size (ft): ', image_width, 'x', image_height)
    draw = ImageDraw.Draw(image)  # edit image to annotate
    fonts_folder = '/Library/Fonts'  # for MAC OS X - folder with the fonts
    arial_font = ImageFont.truetype(os.path.join(fonts_folder, 'Arial Black.ttf'), font_size)  # select the font/size
    draw.text((x, y), text, fill=color, font=arial_font)  # annotate with text
    image.save(out_image, 'PNG')  # save new image


def main():
    """
    Automated Guided Vehicles (AGVs) are critical to the engine manufacturing process. Each AGV hosts one or more
    Programmable Logic Controllers (PLCs) that use wireless to communicate with Human Machine Interfaces (HMIs)
    connected to the plant automation network. Manufacturing lines will stop if there is a interruption
    of communication.

    We can automate the steps required to detect and quick start the troubleshooting of the disconnected PLC.
    The script will:

    - Find out the disconnected AGV number and the IP address using a database lookup
    - Provide the last known location information from CMX
    - Access Point reachability status
    - Access switch reachability and switchport status
    - Create a Spark Room and invite engineering resources
    - Notification using Tropo

    This approach could be applied for monitoring of any critical wireless assets in healthcare, financial,
    retail and utilities.
    """

    # find the floor map where the AGV's are located

    plant_floor_map = 'PlantFloor.png'
    ap_floor_map = 'APFloorMap.png'
    agv_ap_floor_map = 'APAGVFloorMap.png'

    campus = 'Portland'
    building = 'Plant'
    floor = 'Manufacturing'

    get_cmx_map(campus, building, floor, plant_floor_map)

    # change directory to working directory
    os.chdir('/Users/gzapodea/PythonCode/DEVNET_2049/')

    # init script with lab information for AGV's

    agv_ini_mac_list = []
    all_client = all_client_number()

    # find out if an AGV is disconnected

    disconnected_agv_info = {}
    agv_ini_mac_list = mde_initial_info()

    disconnected_agv_info = check_missing_agv(agv_ini_mac_list)

    ap_mac_address = disconnected_agv_info['ap_mac']
    agv_mac_address = disconnected_agv_info['client_mac']
    agv_ip_address = disconnected_agv_info['ip_address']
    agv_band = disconnected_agv_info['band']
    agv_x = disconnected_agv_info['x']
    agv_y = disconnected_agv_info['y']
    agv_cart_number = AGV_DICT[disconnected_agv_info['client_mac']]

    # create APIC EM service ticket

    ticket = get_service_ticket()

    # create Spark Room for the event

    spark_room_id = create_spark_room(ROOM_NAME)

    # update room with info regarding the outage

    post_message(spark_room_id, 'Total Number of clients: ' + str(all_client))
    post_message(spark_room_id, 'Number of AGVs: ' + str(len(AGV_DICT)))
    post_message(spark_room_id, '     ')

    post_message(spark_room_id, 'Disconnected AGV info: ')
    post_message(spark_room_id, 'Cart Number: ' + str(agv_cart_number))
    post_message(spark_room_id, 'MAC Address: ' + str(agv_mac_address))
    post_message(spark_room_id, 'IP Address: ' + str(agv_ip_address))
    post_message(spark_room_id, '802.11 Radio: ' + str(agv_band))

    post_message(spark_room_id, 'X Coordinate: ' + str(int(agv_x)))
    post_message(spark_room_id, 'Y Coordinate: ' + str(int(agv_y)))
    post_message(spark_room_id, '     ')

    post_message(spark_room_id, 'Last connected AP: ')
    post_message(spark_room_id, 'MAC Address: ' + str(ap_mac_address))
    ap_status = check_ap_status(ap_mac_address, ticket)

    ap_name = ap_status[1]
    ap_reachability = ap_status[2]

    post_message(spark_room_id, 'AP Name: ' + ap_name)
    post_message(spark_room_id, 'AP Reachability Status: ' + ap_reachability)

    ap_x_coord = get_cmx_ap_info(campus, building, floor, ap_name)[0]
    ap_y_coord = get_cmx_ap_info(campus, building, floor, ap_name)[1]
    post_message(spark_room_id, 'AP X Coordinate: ' + str(int(ap_x_coord)))
    post_message(spark_room_id, 'AP Y Coordinate: ' + str(int(ap_y_coord)))

    image_process_annotate(plant_floor_map, ap_floor_map, ap_name, 'purple', 12, ap_x_coord, ap_y_coord)
    image_process_annotate(ap_floor_map, agv_ap_floor_map, ('AGV # ' + str(agv_cart_number)), 'red', 16, agv_x, agv_y)

    post_spark_room_file(spark_room_id, agv_ap_floor_map, 'image/png', '/Users/gzapodea/PythonCode/DEVNET_2049/')

    ap_id = ap_status[0]

    switch_status = check_switch_status(ap_id, ticket)
    post_message(spark_room_id, '     ')
    post_message(spark_room_id, 'Access Switch: ')
    access_switch_name = switch_status[0]
    post_message(spark_room_id, 'Switch Name: ' + access_switch_name)
    post_message(spark_room_id, 'Switch Management IP: ' + switch_status[1])
    post_message(spark_room_id, 'Switch Reachability Status: ' + switch_status[2])
    post_message(spark_room_id, 'Switchport: ' + switch_status[3])
    post_message(spark_room_id, 'Switchport status: ' + switch_status[4])

    # sync switch config with APIC-EM

    sync_device(access_switch_name, ticket)

    # invite IT and OT engineers

    add_membership(spark_room_id, IT_ENG_EMAIL)
    add_membership(spark_room_id, OT_ENG_EMAIL)

    # Tropo notification - voice call

    voice_notification_result = tropo_notification()
    post_message(spark_room_id, 'Tropo Voice Notification: ' + voice_notification_result)

    # waiting for device sync

    print('Waiting for device to sync the configuration with APIC-EM')
    time.sleep(60)

    # check Path visualization

    path_visualisation_id = create_path_visualisation(HMI, agv_ip_address, ticket)
    print('The APIC-EM Path Visualisation started, id: ', path_visualisation_id)

    print('Wait for Path Visualization to complete')
    time.sleep(10)

    path_visualisation_status = get_path_visualisation_info(path_visualisation_id, ticket)[0]
    print('Path visualisation status: ', path_visualisation_status)
    path_visualisation_info = get_path_visualisation_info(path_visualisation_id, ticket)[1]
    print('Path visualisation details: ')
    pprint(path_visualisation_info)
    post_message(spark_room_id, str(path_visualisation_info))

    # post tools links for convenience

    post_message(spark_room_id, 'Prime Infrastructure: ' + 'https://172.16.11.25')
    post_message(spark_room_id, 'APIC-EM controller: ' + 'https://172.16.11.30')
    post_message(spark_room_id, 'CMX: ' + 'https://172.16.11.27')
    post_message(spark_room_id, 'WLC management: ' + 'https://172.16.11.26')

    # Optional to delete room at the end of the demo

    input_text = input("If you want to delete this room enter y  ")
    if input_text == 'y':
        delete_room(spark_room_id)

    print('\nEnd of Application run')

if __name__ == '__main__':
    main()
