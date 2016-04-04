import logging
import utils
from yadage.yadagestep import yadagestep

log = logging.getLogger(__name__)

handlers,scheduler = utils.handler_decorator()

### A scheduler does the following things:
###   - attached new nodes to the DAG
###   - for each added step
###     - the step is given a name
###     - the step attributes are determined using the scheduler spec and context
###     - a list of used inputs (in the form of [stepname,outputkey,index])

@scheduler('zip-from-dep')
def zip_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via zip_from_dep_output')

    zipped_maps = []

    stepname = '{}'.format(stage['name'])
    task     = yadagestep(stepname,sched_spec['step'],context)
    
    ### we loop each zip pattern
    for zipconfig in sched_spec['zip']:
        ### for each dependent stage we loop through its steps
        dependencies = [s for s in workflow['stages'] if s['name'] in zipconfig['from_stages']]
        outputs = zipconfig['outputs']

        collected_inputs = []
        for output,reference in utils.regex_match_outputs(dependencies,[outputs]):
            collected_inputs += [output]
            task.used_input(*reference)
            
        zipwith = zipconfig['zip_with']
        newmap = dict(zip(zipwith,collected_inputs))
        log.debug('zipped map %s',newmap)
        zipped_maps += [newmap]
            
    attributes = utils.evaluate_parameters(stage['parameters'],context)
    for zipped in zipped_maps:
        attributes.update(**zipped)
    
    node = utils.addTask(dag,task.s(**attributes))
    stage['scheduled_steps'] = [node]
    
@scheduler('reduce-from-dep')
def reduce_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via reduce_from_dep_output')
    dependencies = [s for s in workflow['stages'] if s['name'] in sched_spec['from_stages']]
    
    stepname = '{}'.format(stage['name'])
    task = yadagestep(stepname,sched_spec['step'],context)

    outputs = sched_spec['outputs']

    collected_inputs = []
    for output,reference in utils.regex_match_outputs(dependencies,[outputs]):
        collected_inputs += [output]
        task.used_input(*reference)

    to_input = sched_spec['to_input']
    attributes = utils.evaluate_parameters(stage['parameters'],context)
    attributes[to_input] = collected_inputs

    node = utils.addTask(dag,task.s(**attributes))
    stage['scheduled_steps'] = [node]
    
@scheduler('map-from-dep')
def map_from_dep_output(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via map_from_dep_output')
    
    dependencies = [s for s in workflow['stages'] if s['name'] in sched_spec['from_stages']]
    
    outputs           = sched_spec['outputs']
    to_input          = sched_spec['to_input']
    stepname_template = stage['name']+'_{index}'
    stage['scheduled_steps'] = []

    for index,(output,reference) in enumerate(utils.regex_match_outputs(dependencies,[outputs])):
        withindex = context.copy()
        withindex.update(index = index)
        attributes = utils.evaluate_parameters(stage['parameters'],withindex)
        attributes[to_input] = output

        task = yadagestep(stepname_template.format(index = index),sched_spec['step'],context)
        task.used_input(*reference)
        node = utils.addTask(dag,task.s(**attributes))
        stage['scheduled_steps'] += [node]

@scheduler('single-from-ctx')
def single_step_from_context(workflow,stage,dag,context,sched_spec):
    log.info('scheduling via single_step_from_context')
    stepname = '{}'.format(stage['name'])

    task = yadagestep(stepname,sched_spec['step'],context)
    attributes = utils.evaluate_parameters(stage['parameters'],context)

    node = utils.addTask(dag,task.s(**attributes))
    stage['scheduled_steps'] = [node]

@scheduler('map-from-ctx')
def map_step_from_context(workflow,stage,dag,context,sched_spec):
    log.info('map_step_from_context')
    
    mappar = sched_spec['map_parameter']
    to_input = sched_spec['to_input']
    stepname_template = stage['name']+'_{index}'
    
    allpars = utils.evaluate_parameters(stage['parameters'],context)
    parswithoutmap = allpars.copy()
    parswithoutmap.pop(mappar)
    
    stage['scheduled_steps'] = []
    for index,p in enumerate(allpars[mappar]):
        withindex = context.copy()
        withindex.update(index = index)
        attributes = parswithoutmap
        attributes[to_input] = p
        
        task = yadagestep(stepname_template.format(index = index),sched_spec['step'],context)
        step = utils.addTask(dag,task.s(**attributes))
        stage['scheduled_steps'] += [step]
