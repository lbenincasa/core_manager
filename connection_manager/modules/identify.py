#!/usr/bin/python3

import platform 
from helpers.commander import send_at_com, shell_command
from helpers.yamlio import *
from helpers.queue import queue
from helpers.exceptions import *
from helpers.modem_support import ModemSupport
from helpers.config_parser import *


system_id = {
    "platform" : "",
    "arc" : "",
    "kernel" : "",
    "host_name" : "",
    "modem_info" : "",
    "modem_vendor" : "",
    "modem_vendor_id" : "",
    "modem_product_id" : "",
    "imei" : "",
    "ccid" : "",
    "sw_version" : "",
}


def identify_setup():

    send_at_com("ATE0", "OK") # turn off modem input echo

    # Modem identification
    # -----------------------------------------
    logger.info("[?] System identifying...")
    
    # Vendor Name
    logger.debug("[+] Modem vendor name")
    system_id["modem_vendor"] = ""
    output = shell_command("lsusb")

    if output[2] == 0:
        for vendor in ModemSupport.vendors:
            if output[0].find(vendor.name) != -1:
                system_id["modem_vendor"] = vendor.name
                
        if system_id["modem_vendor"] == "":  
            raise ModemNotSupported("Modem is not supported!")
            
    else:
        raise RuntimeError("Error occured on lsusb command!")


    # Product Name
    logger.debug("[+] Product Name")
    system_id["modem_name"] = ""
    output = shell_command("usb-devices")
    if output[2] == 0:
        for vendor in ModemSupport.vendors:
            for key in vendor.modules:
                product_name = key.split("_")[0]
                if output[0].find(product_name) != -1:
                    #print(product_name)
                    system_id["modem_name"] = str(product_name)

        if system_id["modem_name"] == "":
            # raise ModemNotSupported("Modem is not supported!")
            logger.warning("Modem name is unknown!")

    else:
        raise RuntimeError("Error occured on usb-devices command!")


    # Vendor ID & Product ID
    logger.debug("[+] Modem vendor id and product id")
    system_id["modem_product_id"] = ""
    output = shell_command("usb-devices")

    if output[2] == 0:
        for vendor in ModemSupport.vendors:
            if output[0].find(vendor.vendor_id) != -1:
                system_id["modem_vendor_id"] = vendor.vendor_id
                
        if system_id["modem_vendor_id"] == "":  
            raise ModemNotSupported("Modem is not supported!")

        for vendor in ModemSupport.vendors:
            for key in vendor.modules:
                if output[0].find(vendor.modules[key]) != -1:
                    system_id["modem_product_id"] = str(vendor.modules[key])
            
        if system_id["modem_product_id"] == "":
            raise ModemNotSupported("Modem is not supported!")

    else:
        raise RuntimeError("Error occured on usb-devices command!")

    
    # Modem Info Text
    logger.debug("[+] Modem info")
    system_id["modem_info"] = ""
    output = send_at_com("AT+GMM", "OK")
    
    if output[2] == 0:
        for vendor in ModemSupport.vendors:
            for key in vendor.modules:
                product_name = key.split("_")[0]
                if output[0].find(product_name) != -1:
                    #print(product_name)
                    system_id["modem_info"] = system_id["modem_vendor"] + " " + product_name
                
        if system_id["modem_info"] == "":
            raise ModemNotSupported("Modem is not supported!")
    else:
        raise RuntimeError("Error occured on usb-devices command!")

    
    # IMEI
    logger.debug("[+] IMEI")
    output = send_at_com("AT+CGSN","OK")
    raw_imei = output[0] if output[2] == 0 else "" 
    imei_filter = filter(str.isdigit, raw_imei)
    system_id["imei"] = "".join(imei_filter)
    
    
    # SW version
    logger.debug("[+] Modem firmware revision")
    output = send_at_com("AT+CGMR","OK")
    system_id["sw_version"] = output[0].split("\n")[1] if output[2] == 0 else ""

    # SIM identification
    # -----------------------------------------
    # CCID
    logger.debug("[+] SIM UCCID")
    output = send_at_com("AT+CCID","OK")
    raw_ccid = output[0] if output[2] == 0 else ""
    ccid_filter = filter(str.isdigit, raw_ccid)
    system_id["ccid"] = "".join(ccid_filter)

    # OS identification
    # -----------------------------------------
    try:
        logger.debug("[+] OS artchitecture")
        system_id["arc"] = str(platform.architecture()[0])
        
        logger.debug("[+] Kernel version")
        system_id["kernel"] = str(platform.release())
        
        logger.debug("[+] Host name")
        system_id["host_name"] = str(platform.node())
        
        logger.debug("[+] OS platform")
        system_id["platform"] = str(platform.platform())
    except Exception as e:
        logger.error("Error occured while getting OS identification!")
        raise RuntimeError("Error occured while getting OS identification!")

    if DEBUG == True and VERBOSE_MODE == True:
        print("")
        print("********************************************************************")
        print("[?] IDENTIFICATION REPORT")
        print("-------------------------")
        for x in system_id.items():
            print(str("[+] " + x[0]) + " --> " + str(x[1]))
        print("********************************************************************")
        print("")


    for key in system_id:
        if system_id[key] == "":
            logger.error("Identification failed!")

            if key == "ccid":
                logger.error("SIM couldn't be identified!")

            raise RuntimeError("Identification failed!")

    try:
        write_yaml_all(SYSTEM_PATH, system_id)
    except Exception as e:
        logger.error(e)
        raise RuntimeError(e)
