from subprocess import check_output

class Modem():
    desc_vendor=None
    desc_product=None

    def __init__(
        self,
        vid,
        pid,
        vendor_name,
        product_name,
        com_ifs
        ):
        self.vid = vid
        self.pid = pid
        self.vendor_name = vendor_name
        self.product_name = product_name
        self.com_ifs = com_ifs

        
supported_modems = [
    # Quectel
    Modem(vid="2c7c", pid="0125", vendor_name="Quectel", product_name="EC25", com_ifs="if02"),
    Modem(vid="2c7c", pid="0121", vendor_name="Quectel", product_name="EC21", com_ifs="if02"),
    Modem(vid="2c7c", pid="0296", vendor_name="Quectel", product_name="BG96", com_ifs="if02"),
    Modem(vid="2c7c", pid="0700", vendor_name="Quectel", product_name="BG95", com_ifs="if02"),
    Modem(vid="2c7c", pid="0306", vendor_name="Quectel", product_name="EP06", com_ifs="if02"),
    Modem(vid="2c7c", pid="0800", vendor_name="Quectel", product_name="RM5XXQ", com_ifs="if02"),

    # Telit
    Modem(vid="1bc7", pid="1201", vendor_name="Telit", product_name="LE910Cx RMNET", com_ifs="if04"), # rmnet
    Modem(vid="1bc7", pid="1203", vendor_name="Telit", product_name="LE910Cx RNDIS", com_ifs="if05"), # rndis
    Modem(vid="1bc7", pid="1204", vendor_name="Telit", product_name="LE910Cx MBIM", com_ifs="if05"), # mbim
    Modem(vid="1bc7", pid="1206", vendor_name="Telit", product_name="LE910Cx ECM", com_ifs="if05"), # ecm
    Modem(vid="1bc7", pid="1031", vendor_name="Telit", product_name="LE910Cx ThreadX RMNET", com_ifs="if02"), # rmnet
    Modem(vid="1bc7", pid="1033", vendor_name="Telit", product_name="LE910Cx ThreadX ECM", com_ifs="if02"), # ecm
    Modem(vid="1bc7", pid="1034", vendor_name="Telit", product_name="LE910Cx ThreadX RMNET", com_ifs="if00"), # rmnet
    Modem(vid="1bc7", pid="1035", vendor_name="Telit", product_name="LE910Cx ThreadX ECM", com_ifs="if00"), # ecm
    Modem(vid="1bc7", pid="1036", vendor_name="Telit", product_name="LE910Cx ThreadX OPTION ONLY", com_ifs="if00"), # just option driver

    Modem(vid="1bc7", pid="1101", vendor_name="Telit", product_name="ME910C1", com_ifs="if01"),
    Modem(vid="1bc7", pid="1102", vendor_name="Telit", product_name="ME910C1", com_ifs="if01"),

    Modem(vid="1bc7", pid="1052", vendor_name="Telit", product_name="FN980 RNDIS", com_ifs="if05"), # rndis
    Modem(vid="1bc7", pid="1050", vendor_name="Telit", product_name="FN980 RMNET", com_ifs="if04"), # rmnet
    Modem(vid="1bc7", pid="1051", vendor_name="Telit", product_name="FN980 MBIM", com_ifs="if05"), # mbim
    Modem(vid="1bc7", pid="1053", vendor_name="Telit", product_name="FN980 ECM", com_ifs="if05"), # ecm

    # Thales
    Modem(vid="1e2d", pid="0069", vendor_name="Thales/Cinterion", product_name="PLSx3", com_ifs="if04"), # ecm
    Modem(vid="1e2d", pid="006f", vendor_name="Thales/Cinterion", product_name="PLSx3", com_ifs="if04"), # wwan
]

def get_available_ports():
    ports = check_output("find /sys/bus/usb/devices/usb*/ -name dev", shell=True)
    ports = ports.decode().split("\n")

    available_ports = []

    for port in ports:
        if port.endswith("/dev"):
            port = port[:-4]

        if not port:
            continue

        try:
            device_details = check_output("udevadm info -q property --export -p {}".format(port), shell=True)
        except:
            continue

        device_details = device_details.decode().split("\n")

        _port_details = {}

        for line in device_details:
            if line.startswith("DEVNAME="):
                _port_details["port"] = line[8:].replace("'", "")
            elif line.startswith("ID_VENDOR="):
                _port_details["vendor"] = line[10:].replace("'", "")
            elif line.startswith("ID_VENDOR_ID="):
                _port_details["vendor_id"] = line[13:].replace("'", "")
            elif line.startswith("ID_MODEL="):
                _port_details["model"] = line[9:].replace("'", "")
            elif line.startswith("ID_MODEL_FROM_DATABASE="):
                _port_details["model_from_database"] = line[23:].replace("'", "")
            elif line.startswith("ID_MODEL_ID="):
                _port_details["product_id"] = line[12:].replace("'", "")
            elif line.startswith("ID_USB_INTERFACE_NUM="):
                _port_details["interface"] = "if"+line[21:].replace("'", "")
            elif line.startswith("ID_USB_VENDOR_ID="):
                _port_details["ID_USB_VENDOR_ID"] = line[17:].replace("'", "")
            elif line.startswith("ID_USB_MODEL_ID="):
                _port_details["ID_USB_MODEL_ID"] = line[16:].replace("'", "")

        if "bus" not in _port_details["port"]:
            available_ports.append(_port_details)

    return available_ports


def find_cellular_modem():
    """function to find supported modem"""
    output = check_output("lsusb", shell=True).decode()

    for modem in supported_modems:
        if output.find(modem.vid) != -1 and output.find(modem.pid) != -1:
            return modem
    raise Exception("No supported modem exist!")


def decide_port():
    """function to decide port name of supported modem"""
    try:
        modem = find_cellular_modem()
    except:
        return (None, None)
    else:
        ports = get_available_ports()
        for port in ports:
            if  modem.com_ifs in port.values() and \
                modem.vid in port.values() and \
                modem.pid in port.values():

                port_name = port.get("port")
                modem.desc_vendor = port.get("vendor")
                modem.desc_product = port.get("model", port.get("model_from_database"))
                return (port_name, modem)
        return (None, None)