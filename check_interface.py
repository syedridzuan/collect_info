from jnpr.junos import Device
import re
from datetime import datetime
import os
from lib.mylogger import MyLogger
import pickle
from pprint import pprint as pp
import yaml

log = MyLogger("log", "collect.log")
logger = log.getlogger()

now = datetime.now()
logger.info(now)
folder_cdt = now.strftime("%d-%m-%Y-%H-%M-%S")

logger.info(folder_cdt)

dir_path = os.path.dirname(os.path.realpath(__file__))

final_path = os.path.join(dir_path, folder_cdt)

try:
    os.stat(final_path)
except:
    os.mkdir(final_path)


def main():
    global dev
    global interface
    global config

    config = get_config("config.yaml")['config']

    build_command()

    flap_info = read_file()
    logger.info(flap_info)
    dev = Device(host=config['host'], user=config['username'], password=config['password'])
    dev.open()

    if flap_info['last_detected']:
        last_detect = datetime.strptime(flap_info['last_detected'], '%Y-%m-%d %H:%M:%S')
        last_detect_diff = (now - last_detect).total_seconds()

    else:
        last_detect_diff = -1

    logger.info("Last detected diff in seconds :{}".format(last_detect_diff))

    admin_status, oper_status, last_flap = check_interface()

    logger.info("admin status:{}, oper status:{}, last flap:{}"
                .format(admin_status, oper_status, last_flap))

    last_flap_prev = flap_info['last_flap']
    print(last_flap, last_flap_prev)

    if admin_status == "down" or oper_status == "down":
        logger.info("interface down, waiting to be up again")
    else:
        if last_flap == last_flap_prev:
            logger.info("No changes")

        elif last_detect_diff > config['last_detect_diff_seconds'] :
            logger.info("Changes detected")
            flap_info['last_flap'] = last_flap
            flap_info['last_detected'] = now.strftime('%Y-%m-%d %H:%M:%S')
            exec_command(COMMANDS)
            index_no = get_index()
            command2 = build_2ndcommand(index_no, config['fpc'])
            exec_command(command2)
            write_to_file(flap_info)
        else:
            logger.info("Changes detected, but within ignore period")
            flap_info['last_flap'] = last_flap
            flap_info['last_detected'] = now.strftime('%Y-%m-%d %H:%M:%S')
            write_to_file(flap_info)

    logger.info(flap_info)


def get_config(file):
    with open(file, 'r') as stream:
        try:
            data = (yaml.load(stream))
        except Exception as exc:
            print(exc)
            data = None
    return data

def build_command():

    global COMMANDS

    COMMANDS = ['show krt queue',
                'show krt state',
                'show route summary',
                'show route receive-protocol bgp {}'.format(config['bgp_ip']),
                'show route advertising-protocol bgp {}'.format(config['bgp_ip']),
                "show mpls lsp ingress extensive | no-more",
                "show mpls lsp ingress name {} extensive | no-more".format(config['lsp']),
                "show rsvp session ingress",
                "show rsvp session ingress name {} extensive | no-more".format(config['lsp']),
                'show interfaces extensive | match "Physical|Input bytes|Output bytes" | no-more',
                ]


def build_2ndcommand(index_id, fpc):

    command1 = ('request pfe execute '
               'command "show nhdb id {} extensive"'
               ' target {}'
                .format(index_id, fpc))

    command2 = ('show route forwarding-table destination {} | no-more'.format(index_id))

    command3 = ('request pfe execute command '
                '"show nhdb hw unilist-sel '
                'extensive" target {}'
                .format(fpc))

    # command4 = ('request pfe execute command '
    #             '"write core" '
    #             'target {}'
    #             .format(fpc))

    command5 = "show system core-dumps"

    return [command1, command2, command3, command5]


def get_index():
    print("getting index no")
    result = dev.rpc.get_route_information(destination=config['problemetic_ip'], extensive=True)
    rt_entry = result.find(".//rt-entry")
    for item in rt_entry:
        #print(item.tag)
        if item.tag == "nh-type" and item.text=="Router":
            return item.getnext().text


def exec_command(my_command):
    for command in my_command:
        logger.info(command)
        result = dev.cli(command)
        f_name = os.path.join(final_path, convert_file_name(command))
        with open(f_name, 'w') as the_file:
            the_file.write(result)


def convert_file_name(f_name):
    match = [" ", "-", "|"]
    f_name = f_name.replace('"', "")

    for item in match:
        f_name = f_name.replace(item, "_")
    return f_name + ".txt"


def check_interface():
    result = dev.rpc.get_interface_information(interface_name=config['if_name'], normalize=True)
    last_flap = result.findtext(".//interface-flapped")
    admin_status = result.findtext(".//admin-status")
    oper_status = result.findtext(".//oper-status")
    last_flap = re.search('\d+-\d+-\d+ \d+:\d+:\d+', last_flap).group(0).strip()
    return admin_status, oper_status, last_flap


def write_to_file(flap_info):
    pickle.dump(flap_info, open("flap_info.p", "wb"))


def read_file():
    flap_info = {'last_flap': None,
                 'last_detected': None}

    try:
        pickle.load(open("flap_info.p", "rb"))
    except IOError:
        pickle.dump(flap_info, open("flap_info.p", "wb"))
    else:
        flap_info = pickle.load(open("flap_info.p", "rb"))

    return flap_info


if __name__ == "__main__":
   main()
