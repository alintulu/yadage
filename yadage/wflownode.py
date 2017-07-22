import adage.node
import os
import jsonpointer
import tasks
import datetime
import time

class YadageNode(adage.node.Node):
    '''
    Node object for yadage that extends the default with
    the ability to have prepublished results
    '''

    def __init__(self, name, task, identifier=None):
        super(YadageNode, self).__init__(name, task, identifier)

    def __repr__(self):
        lifetime = datetime.timedelta(seconds = (time.time() - self.define_time))
        runtime = None
        if self.state != adage.nodestate.DEFINED:
            referencetime = time.time() if not self.ready() else self.ready_by_time
            runtime = datetime.timedelta(seconds = (referencetime - self.submit_time))
        return '<YadageNode {} {} lifetime: {}  runtime: {} (id: {}) has result: {}>'.format(
            self.name, self.state, lifetime, runtime, self.identifier, self.has_result()
        )

    def has_result(self):
        if 'YADAGE_IGNORE_PREPUBLISHING' in os.environ:
            return self.successful()
        return (self.task.prepublished is not None) or self.successful()

    @property
    def result(self):
        if self.task.prepublished is not None and 'YADAGE_IGNORE_PREPUBLISHING' not in os.environ:
            if self.ready() and self.successful():
                sanity =  super(YadageNode, self).result == self.task.prepublished
                if not sanity:
                    raise RuntimeError('prepublished and actual result differ:\nlhs:\n{}\nrhs:{}'.format(
                        super(YadageNode, self).result,self.task.prepublished)
                )
            return self.task.prepublished
        return super(YadageNode, self).result

    def readfromresult(self,pointerpath, whoisreading = None, failsilently = False):
        if not self.has_result():
            if failsilently: return None
            raise RuntimeError('attempt')
        pointer = jsonpointer.JsonPointer(pointerpath)
        if whoisreading:
            whoisreading.inputs.append(tasks.outputReference(self.identifier,pointer))
        v = pointer.resolve(self.result)
        return v

    @classmethod
    def fromJSON(cls, data):
        if data['task']['type'] == 'init_task':
            task = tasks.init_task.fromJSON(data['task'])
        elif data['task']['type'] == 'packtivity_task':
            task = tasks.packtivity_task.fromJSON(data['task'])
        else:
            raise RuntimeError('unknown task type',data['task']['type'])
        return cls(data['name'], task, data['id'])
