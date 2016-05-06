import logging
import adage.backends
import yadage.yadagestep
from packtivity import packtivity_callable
log = logging.getLogger(__name__)

class JSONResultProxy(object):
    def __init__(self,task,multiprocprox,prepublished = None):
        self.proxy = multiprocprox

class JSONBackend(object):
    def __init__(self,nparallel = 2):
        self.multiproc = adage.backends.MultiProcBackend(nparallel)
        
    def submit(self,task):
        if type(task) == yadage.yadagestep.yadagestep:
            acallable = packtivity_callable(task.name,task.spec,task.attributes,task.context)
        else:
            acallable = task
        multiprocprox = self.multiproc.submit(acallable)
        return JSONResultProxy(task,multiprocprox)
        
    def result(self,resultproxy):
        return self.multiproc.result(resultproxy.proxy)
    
    def ready(self,resultproxy):
        return self.multiproc.ready(resultproxy.proxy)
    
    def successful(self,resultproxy):
        return self.multiproc.successful(resultproxy.proxy)
    
    def fail_info(self,resultproxy):
        return self.multiproc.fail_info(resultproxy.proxy)
