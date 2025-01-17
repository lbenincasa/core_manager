#!/usr/bin/python3

import time

from helpers.config_parser import conf
from helpers.logger import logger
from helpers.exceptions import ModemNotFound, ModemNotSupported
from helpers.queue import Queue
from helpers.modem_support.default import BaseModule
from modules.identify import identify_setup, identify_modem
from modules.diagnostic import Diagnostic

queue = Queue()
modem = BaseModule()

NO_WAIT_INTERVAL = 0.1
#SECOND_CHECK_INTERVAL = 10
SECOND_CHECK_INTERVAL = 2

first_connection_flag = False
soft_reboot_count = 0
check_internet_cnt = 0

logger.info("Core Manager started.")


def _organizer():
    if queue.base == "organizer":
        #Beni, was: queue.sub = "identify_modem"
        #step eseguito al primo avvio del sistema
        queue.sub = "check_internet_init"
        queue.wait = NO_WAIT_INTERVAL
    else:
        if queue.is_ok: #OK --> next step is 'success'
            queue.sub = queue.success
            queue.is_ok = False
        else:
            if queue.counter >= queue.retry: #NOK --> too many retries, next step is 'fail'
                queue.sub = queue.fail
                queue.clear_counter()
                #queue.interval = NO_WAIT_INTERVAL
                queue.wait = NO_WAIT_INTERVAL
            else: #NOK --> retrying, next step is 'base' (the current one)
                queue.sub = queue.base
                queue.counter_tick()
                queue.wait = queue.interval

                # Exception for the second chance of internet control
                if queue.base == "check_internet_base":
                    #Beni, was: queue.interval = SECOND_CHECK_INTERVAL
                    queue.wait = SECOND_CHECK_INTERVAL


def _identify_modem():
    global modem
    queue.set_step(
        sub="organizer",
        base="identify_modem",
        success="identify_setup",
        fail="diagnose_last_exit",
        wait=NO_WAIT_INTERVAL,
        interval=2,
        is_ok=False,
        retry=20,
    )

    try:
        module = identify_modem()
    except Exception as error:
        logger.error("identify_modem -> %s", error)
        queue.is_ok = False
    else:
        modem = module
        queue.is_ok = True
        logger.info(" identified modem: %s", modem.module_name)


def _identify_setup():
    global modem
    queue.set_step(
        sub="organizer",
        base="identify_setup",
        success="configure_modem",
        fail="diagnose_last_exit",
        wait=NO_WAIT_INTERVAL,
        interval=2,
        is_ok=False,
        retry=20,
    )

    try:
        new_id = identify_setup()
    except Exception as error:
        logger.error("identify_setup -> %s", error)
        queue.is_ok = False
    else:
        if new_id != {}:
            modem.imei = new_id.get("imei", "")
            modem.iccid = new_id.get("iccid", "")
            modem.sw_version = new_id.get("sw_version", "")
        queue.is_ok = True

        if conf.debug_mode and conf.verbose_mode:
            print("")
            print("********************************************************************")
            print("[?] MODEM REPORT")
            print("-------------------------")
            attrs = vars(modem)
            print("\n".join("[+] %s : %s" % item for item in attrs.items()))
            print("********************************************************************")
            print("")


def _configure_modem():
    queue.set_step(
        sub="organizer",
        base="configure_modem",
        success="check_sim_ready",
        fail="diagnose_repeated",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=5,
    )

    try:
        modem.configure_modem()
    except ModemNotSupported:
        queue.is_ok = False
    except ModemNotFound:
        queue.is_ok = False
    except Exception as error:
        logger.error("configure_modem() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _check_sim_ready():
    queue.set_step(
        sub="organizer",
        base="check_sim_ready",
        success="check_network",
        fail="diagnose_repeated",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=5,
    )

    try:
        modem.check_sim_ready()
    except Exception as error:
        logger.error("check_sim_ready() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _check_network():
    queue.set_step(
        sub="organizer",
        base="check_network",
        success="initiate_ecm",
        fail="diagnose_repeated",
        wait=NO_WAIT_INTERVAL,
        interval=5,
        is_ok=False,
        retry=180, # 15 minutes
    )

    try:
        modem.check_network()
    except Exception as error:
        logger.error("check_network() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _initiate_ecm():
    queue.set_step(
        sub="organizer",
        base="initiate_ecm",
#        success="check_internet_base",
        success="initiate_gps",
        fail="diagnose_repeated",
        wait=NO_WAIT_INTERVAL,
        interval=0.1,
        is_ok=False,
        retry=5,
    )

    try:
        modem.initiate_ecm()
    except Exception as error:
        logger.error("initiate_ecm() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True

def _initiate_gps():
    queue.set_step(
        sub="organizer",
        base="initiate_ecm",
        success="check_internet_base",
        fail="diagnose_repeated",
        wait=NO_WAIT_INTERVAL,
        interval=0.1,
        is_ok=False,
        retry=5,
    )

    try:
        modem.initiate_gps()
    except Exception as error:
        logger.error("initiate_gps() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True



def _check_internet():
    global first_connection_flag
    global soft_reboot_count
    global check_internet_cnt

    if queue.sub == "check_internet_base":
        queue.set_step(
            sub="organizer",
            base="check_internet_base",
            success="check_internet_base",
            fail="diagnose_base",
            wait = conf.check_internet_interval,
            interval = conf.check_internet_interval,
            is_ok=False,
            retry=1,
        )
    elif queue.sub == "check_internet_after_rci":
        queue.set_step(
            sub="organizer",
            base="check_internet_after_rci",
            success="check_internet_base",
            fail="reset_usb_interface",
            wait=NO_WAIT_INTERVAL,
            interval=10,
            is_ok=False,
            retry=0,
        )
    elif queue.sub == "check_internet_after_rui":
        queue.set_step(
            sub="organizer",
            base="check_internet_after_rui",
            success="check_internet_base",
            fail="reset_modem_softly",
            wait=NO_WAIT_INTERVAL,
            interval=10,
            is_ok=False,
            retry=0,
        )
    elif queue.sub == "check_internet_init":
        queue.set_step(
            sub="organizer",
            base="check_internet_init",
            success="identify_modem",
            fail="identify_modem",
            wait=NO_WAIT_INTERVAL,
            interval=1,
            is_ok=False,
            retry=2,
        )

    try:
        res = modem.check_internet()
    except Exception as error:
        logger.error("check_internet() -> %s", error)
        queue.is_ok = False
    else:

        # reset soft_reboot_count
        soft_reboot_count  = 0
        check_internet_cnt += 1

        if (not first_connection_flag) or (check_internet_cnt >= 50):
            interface = "unknown"
            if res == 1:
                interface = "default"
            elif res == 2:
                interface = "cellular"
            logger.info(f"Internet available through the {interface} interface")
            check_internet_cnt = 0
            first_connection_flag = True

        if modem.incident_flag:
            modem.monitor["fixed_incident"] += 1
            modem.incident_flag = False
            logger.info("Internet connection is restored")

        queue.is_ok = True

def _check_internet_init():
    queue.set_step(
        sub="organizer",
        base="check_internet_init",
        success="identify_modem",
        fail="identify_modem",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=2,
    )

    try:
        res = modem.check_internet()
    except Exception as error:
        logger.error("check_interne_initt() -> %s", error)
        queue.is_ok = False
    else:

        interface = "unknown"
        if res == 1:
            interface = "default"
        elif res == 2:
            interface = "cellular"
        logger.info(f"Init: internet available through the {interface} interface")
        queue.is_ok = True



def _diagnose():
    modem.monitor["cellular_connection"] = False
    modem.incident_flag = True
    diag_type = 0
    diag = Diagnostic(modem)

    if queue.sub == "diagnose_base":
        queue.set_step(
            sub="organizer",
            base="diagnose_base",
            success="reset_connection_interface",
            fail="reset_connection_interface",
            wait=NO_WAIT_INTERVAL,
            interval=0.1,
            is_ok=False,
            retry=5,
        )
        diag_type = 0
    elif queue.sub == "diagnose_repeated":
        queue.set_step(
            sub="organizer",
            base="diagnose_repeated",
            success="reset_modem_softly",
            fail="reset_modem_softly",
            wait=NO_WAIT_INTERVAL,
            interval=0.1,
            is_ok=False,
            retry=5,
        )
        diag_type = 1
    elif queue.sub == "diagnose_last_exit":
        queue.set_step(
            sub="organizer",
            base="diagnose_last_exit",
            success="reset_modem_hardly",
            fail="reset_modem_hardly",
            wait=NO_WAIT_INTERVAL,
            interval=0.1,
            is_ok=False,
            retry=5,
        )
        diag_type = 1

    try:
        diag.diagnose(diag_type)
    except Exception as error:
        logger.error("diagnose() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _reset_connection_interface():
    queue.set_step(
        sub="organizer",
        base="reset_connection_interface",
        success="check_internet_after_rci",
        fail="reset_usb_interface",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=2,
    )

    try:
        modem.reset_connection_interface()
    except Exception as error:
        logger.error("reset_connection_interface() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _reset_usb_interface():
    queue.set_step(
        sub="organizer",
        base="reset_usb_interface",
        success="check_internet_after_rui",
        fail="reset_modem_softly",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=2,
    )

    try:
        modem.reset_usb_interface()
    except Exception as error:
        logger.error("reset_usb_interface() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


def _reset_modem_softly():
    global soft_reboot_count
    soft_reboot_count += 1

    # If soft_reboot_count is 2, that means the modem has been rebooted twice.
    # Manager try to reboot the modem hardly to solve the problem that couldn't
    # be solved by soft reboot.
    if soft_reboot_count == 2:
        queue.set_step(
            sub="organizer",
            base="reset_modem_softly",
            success="identify_modem",
            fail="reset_modem_hardly",
            wait=NO_WAIT_INTERVAL,
            interval=1,
            is_ok=False,
            retry=1,
        )
        logger.info("Jump to reset_modem_hardly for 2nd trial of rebooting modem!")

        try:
            modem.reset_modem_hardly()
        except Exception as error:
            logger.error("reset_modem_hardly() -> %s", error)
            queue.is_ok = False
        else:
            queue.is_ok = True

    else:
        queue.set_step(
            sub="organizer",
            base="reset_modem_softly",
            success="identify_modem",
            fail="reset_modem_hardly",
            wait=NO_WAIT_INTERVAL,
            interval=1,
            is_ok=False,
            retry=1,
        )

        try:
            modem.reset_modem_softly()
        except Exception as error:
            logger.error("reset_modem_softly() -> %s", error)
            queue.is_ok = False
        else:
            queue.is_ok = True


def _reset_modem_hardly():
    queue.set_step(
        sub="organizer",
        base="reset_modem_hardly",
        success="identify_modem",
        fail="identify_modem",
        wait=NO_WAIT_INTERVAL,
        interval=1,
        is_ok=False,
        retry=1,
    )

    try:
        modem.reset_modem_hardly()
    except Exception as error:
        logger.error("reset_modem_hardly() -> %s", error)
        queue.is_ok = False
    else:
        queue.is_ok = True


steps = {
    "organizer": _organizer,  # 0
    "identify_modem": _identify_modem,  # 16
    "identify_setup": _identify_setup,  # 1
    "configure_modem": _configure_modem,  # 2
    "check_sim_ready": _check_sim_ready,  # 14
    "check_network": _check_network,  # 3
    "initiate_ecm": _initiate_ecm,  # 4
    "check_internet_base": _check_internet,  # 5
    "diagnose_base": _diagnose,  # 6
    "diagnose_repeated": _diagnose,  # 13
    "diagnose_last_exit": _diagnose,  # 15
    "reset_connection_interface": _reset_connection_interface,  # 7
    "check_internet_after_rci": _check_internet,  # 8
    "reset_usb_interface": _reset_usb_interface,  # 9
    "check_internet_after_rui": _check_internet,  # 10
    "reset_modem_softly": _reset_modem_softly,  # 11
    "reset_modem_hardly": _reset_modem_hardly,  # 12
    "check_internet_init": _check_internet_init,  # 0.5
    "initiate_gps": _initiate_gps,  # 4.5
}


def execute_step(step):
    steps.get(step)()


def manage_connection():
    # main execution of step
    if queue.sub == "organizer":
        execute_step(queue.sub)
        #Beni, was: return queue.interval
        return queue.wait
    elif queue.sub == "identify_setup":  # modem identification is OK.
        execute_step(queue.sub)
        #Beni, was: return (queue.interval, modem)
        return (queue.wait, modem)
    # organiser step
    execute_step(queue.sub)
    return NO_WAIT_INTERVAL


if __name__ == "__main__":
    while True:
        res = manage_connection()
        if not isinstance(res, tuple):
            interval = res
        else:
            interval = res[0]
            modem = res[1]
        time.sleep(interval)
