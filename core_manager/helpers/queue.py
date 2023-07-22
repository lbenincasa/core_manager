class Queue:

    sub = "organizer"      #di solito lo step passa sempre per organizer, qui di solito c'e' sempre e solo 'organizer'
    base = "organizer"     #nome dello step attuale
    success = "organizer"  #step dove andare in caso di successo
    fail = "organizer"     #step dove andare in caso di fail
    wait = 0.1             # time to wait to go the next step, default = NO_WAIT
    interval = 0           #retry interval
    retry = 0              #nr of retries to do
    is_ok = False
    counter = 0

    def clear_counter(self):
        self.counter = 0

    def counter_tick(self):
        self.counter += 1

    def set_step(self, sub, base, success, fail, wait=0.1, interval=0, is_ok=False, retry=0):
        self.sub = sub
        self.base = base
        self.success = success
        self.fail = fail
        self.wait = wait
        self.interval = interval
        self.is_ok = is_ok
        self.retry = retry
