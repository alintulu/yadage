import logging
import utils
from yadage.yadagestep import yadagestep

log = logging.getLogger(__name__)

handlers,scheduler = utils.handler_decorator()

### A scheduler does the following things:
###   - creates new tasks (yadagesteps)
###   - figures out attributs to call the task with
###   - keeps track of used inputs
###   - attaches the nodes for this task to the DAG

@scheduler('zip-from-dep')
def zip_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via zip_from_dep_output')
    
    zipped_maps = []
    task = yadagestep(stage['name'],sched_spec['step'],context)
    
    ### we loop each zip pattern
    for zipconfig in sched_spec['zip']:
        ### for each dependent stage we loop through its steps
        dependencies = [s for s in workflow['stages'] if s['name'] in zipconfig['from_stages']]
        
        refgen = utils.regex_match_outputs(dependencies,[zipconfig['outputs']])
        collected_inputs = [utils.read_input(dag,task,reference) for reference in refgen]
                    
        zipped_maps += [dict(zip(zipconfig['zip_with'],collected_inputs))]
        log.info('last zipped map %s',zipped_maps[-1])
            
    attributes = utils.evaluate_parameters(stage['parameters'],context)
    for zipped in zipped_maps:
        attributes.update(**zipped)
    
    utils.addStep(stage,dag,task.s(**attributes))
    
@scheduler('reduce-from-dep')
def reduce_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via reduce_from_dep_output')
    dependencies = [s for s in workflow['stages'] if s['name'] in sched_spec['from_stages']]
    
    task = yadagestep(stage['name'],sched_spec['step'],context)
    
    refgen = utils.regex_match_outputs(dependencies,[sched_spec['outputs']])
    collected_inputs = [utils.read_input(dag,task,reference) for reference in refgen]
    
    to_input = sched_spec['to_input']
    attributes = utils.evaluate_parameters(stage['parameters'],context)
    attributes[to_input] = collected_inputs
    
    utils.addStep(stage,dag,task.s(**attributes))
    
@scheduler('    ')
def map_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via map_from_dep_output')
    
    dependencies = [s for s in workflow['stages'] if s['name'] in sched_spec['from_stages']]
    
    to_input          = sched_spec['to_input']
    stepname_template = stage['name']+' {index}'
    
    for index,reference in enumerate(utils.regex_match_outputs(dependencies,[sched_spec['outputs']])):
        task = yadagestep(stepname_template.format(index = index),sched_spec['step'],context)
        
        withindex = context.copy()
        withindex.update(index = index)
        attributes = utils.evaluate_parameters(stage['parameters'],withindex)
        attributes[to_input] = utils.read_input(dag,task,reference)
        
        utils.addStep(stage,dag,task.s(**attributes))