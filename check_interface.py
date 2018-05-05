from jnpr.junos import Device
from lxml import etree
from jnpr.junos import exception
import pprint
from jnpr.junos.utils.config import Config
import ipaddress
import time
import re
import datetime
import os
from lib.mylogger import MyLogger


log = MyLogger("log", "lldp_audit.log")
logger = log.getlogger()



lsp = "r3-to-r6-af"
bgp_ip = "2.2.2.2"
problemetic_ip = "22.22.22.0"
fpc = "fpc0"

COMMANDS = ['show krt queue',
            'show krt state',
            'show route summary',
            'show route receive-protocol bgp {}'.format(bgp_ip),
            'show route advertising-protocol bgp {}'.format(bgp_ip),
            "show mpls lsp ingress extensive | no-more",
            "show mpls lsp ingress name {} extensive | no-more".format(lsp),
            "show rsvp session ingress",
            "show rsvp session ingress name {} extensive | no-more".format(lsp),
            'show interfaces extensive | match "Physical|Input bytes|Output bytes" | no-more',
            ]

cdt = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
print(cdt)
dir_path = os.path.dirname(os.path.realpath(__file__))
print(dir_path)
final_path = os.path.join(dir_path, cdt)
print(final_path)
try:
    os.stat(final_path)
except:
    os.mkdir(final_path)


def main():
    global dev
    global interface

    dev = Device(host='192.168.122.4', user='lab', password='abc123')
    dev.open()

    last_flap = check_interface()
    last_flap_prev = read_file()
    print(last_flap, last_flap_prev)

    if last_flap == last_flap_prev:
        logger.info("No changes")

    else:
        logger.info("Changes detected")
        exec_command(COMMANDS)
        index_no = get_index()
        command2 = build_2ndcommand(index_no, fpc)
        exec_command(command2)

    write_to_file(last_flap)


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

    command4 = ('request pfe execute command '
                '"write core" '
                'target {}'
                .format(fpc))

    command5 = "show system core-dumps"

    return [command1, command2, command3, command4, command5]


def get_index():
    print("getting index no")
    result = dev.rpc.get_route_information(destination=problemetic_ip, extensive=True)
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
    result = dev.rpc.get_interface_information(interface_name="ge-0/0/0", normalize=True)
    last_flap = result.find(".//interface-flapped")
    return re.search('\d+-\d+-\d+ \d+:\d+:\d+', last_flap.text).group(0).strip()


def write_to_file(text_date):
    with open('last_flap.txt', 'w') as the_file:
        the_file.write(text_date)


def read_file():
    file = open("last_flap.txt", "r")
    x = file.read()
    return x.strip()


if __name__ == "__main__":
   main()
