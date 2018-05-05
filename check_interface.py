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

lsp = "r3-to-r6-af"
bgp_ip = "2.2.2.2"
problemetic_ip = "22.22.22.0"
fpc = "fpc1"

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


# show route x.x.x.x extensive (x.x.x.x is problematic IP)
# request pfe execute command "show nhdb id <index id> extensive" target fpc1 (Index id gets from the above command)
# show route forwarding-table destination x.x.x.x | no-more

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
        print("no changes")
    else:
        print("Changes detected")
        exec_command(COMMANDS)
        index_no = get_index()
        command2 = build_2ndcommand(index_no, fpc)
        exec_command(command2)

    write_to_file(last_flap)


def build_2ndcommand(index_id, fpc):
    command1 = ('request pfe execute '
               'command "show nhdb id <index id> extensive"'
               ' target {}'
                .format(index_id, fpc))

    command2 = ('show route forwarding-table destination {} | no-more'.format(index_id))
    return [command1, command2]


def get_index():
    print("getting index no")
    result = dev.rpc.get_route_information(destination=problemetic_ip, extensive=True)
    nh_index = result.findall(".//nh-index")
    return nh_index[0].text
 
def exec_command(my_command):
    for command in my_command:
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
