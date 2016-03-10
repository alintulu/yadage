import os
import subprocess
import sys
import time
import psutil
import utils
import socket

handlers,environment = utils.handler_decorator()

def prepare_docker(nametag,workdir,global_work,do_cvmfs,do_grid):
    docker_mod = ''
    if not 'YADAYE_WITHIN_DOCKER' in os.environ:
        docker_mod += '-v {}:/workdir'.format(os.path.abspath(global_work))
    else:
        docker_mod += '--volumes-from {}'.format(socket.gethostname())
        
    if do_cvmfs:
        if not 'YADAGE_CVMFS_LOCATION' in os.environ:
            docker_mod+=' -v /cvmfs:/cvmfs'
        else:
            docker_mod+=' -v {}:/cvmfs'.format(os.environ['YADAGE_CVMFS_LOCATION'])
    if do_grid:
        if not 'YADAGE_AUTH_LOCATION' in os.environ:
            docker_mod+=' -v /home/recast/recast_auth:/recast_auth'
        else:
            docker_mod+=' -v {}:/recast_auth'.format(os.environ['YADAGE_AUTH_LOCATION'])

    docker_mod += ' --cidfile {}/{}.cid'.format(workdir,nametag)

    return docker_mod

@environment('docker-encapsulated')
class docker_enc_handler(object):
    def __init__(self,nametag,log):
        self.nametag  = nametag
        self.log  = log

    def __call__(self,environment,context,command):
        log = self.log
        log.info('context: \n {}'.format(context))
        self.workdir = context['workdir']
        self.global_work = context.get('global_workdir',self.workdir)


        container = environment['image']
  
        report = '''\n\
--------------
run in docker container: {container}
with env: {env}
command: {command}
resources: {resources}
--------------
      '''.format( container = container,
                  command = command,
                  env = environment['envscript'] if environment['envscript'] else 'default env',
                  resources = environment['resources']
                )
  
        do_cvmfs = 'CVMFS' in environment['resources']
        do_grid  = 'GRIDProxy'  in environment['resources']
  
        log.info(report)
        log.info('dogrid: {} do_cvmfs: {}'.format(do_grid,do_cvmfs))

        envmod = 'source {} &&'.format(environment['envscript']) if environment['envscript'] else ''

        in_docker_cmd = '{envmodifier} {command}'.format(envmodifier = envmod, command = command)

        docker_mod = prepare_docker(self.nametag,self.workdir,self.global_work,do_cvmfs,do_grid)

        fullest_command = 'docker run --rm {docker_mod} {container} sh -c \'{in_dock}\''.format(docker_mod = docker_mod, container = container, in_dock = in_docker_cmd)
        if do_cvmfs:
            fullest_command = 'cvmfs_config probe && {}'.format(fullest_command)
          # fullest_command = 'eval $(docker-machine env default) && echo cvmfs_config probe && {}'.format(fullest_command)


        docker_pull_cmd = 'docker pull {container}'.format(container = container)

        log.info('docker pull command: \n  {}'.format(docker_pull_cmd))
        log.info('docker run  command: \n  {}'.format(fullest_command))

        try:
          with open('{}/{}.pull.log'.format(self.workdir,self.nametag),'w') as logfile:
            proc = subprocess.Popen(docker_pull_cmd,shell = True, stderr = subprocess.STDOUT, stdout = logfile)
            log.info('started pull subprocess with pid {}. now wait to finish'.format(proc.pid))
            time.sleep(0.5)
            log.info('process children: {}'.format([x for x in psutil.Process(proc.pid).children(recursive = True)]))
            proc.communicate()
            log.info('pull subprocess finished. return code: {}'.format(proc.returncode))
            if proc.returncode:
              log.error('non-zero return code raising exception')
              raise subprocess.CalledProcessError(returncode =  proc.returncode, cmd = docker_pull_cmd)
            log.info('moving on from pull')
        except RuntimeError as e:
          log.info('caught RuntimeError')
          raise e
        except subprocess.CalledProcessError as exc:
          log.error('subprocess failed. code: {},  command {}'.format(exc.returncode,exc.cmd))
          raise RuntimeError('failed docker subprocess in runStep.')
        except:
          log.info("Unexpected error: {}".format(sys.exc_info()))
          raise
        finally:
          log.info('finally for pull')

        try:
            with open('{}/{}.run.log'.format(self.workdir,self.nametag),'w') as logfile:
                proc = subprocess.Popen(fullest_command,shell = True, stderr = subprocess.STDOUT, stdout = logfile)
                log.info('started run subprocess with pid {}. now wait to finish'.format(proc.pid))
                time.sleep(0.5)
                log.info('process children: {}'.format([x for x in psutil.Process(proc.pid).children(recursive = True)]))
                proc.communicate()
                log.info('pull subprocess finished. return code: {}'.format(proc.returncode))
                if proc.returncode:
                    log.error('non-zero return code raising exception')
                    raise subprocess.CalledProcessError(returncode =  proc.returncode, cmd = fullest_command)
                log.info('moving on from run')
        except subprocess.CalledProcessError as exc:
            log.error('subprocess failed. code: {},  command {}'.format(exc.returncode,exc.cmd))
            raise RuntimeError('failed docker subprocess in runStep.')
        except:
            log.error("Unexpected error: {}".format(sys.exc_info()))
            raise
        finally:
            log.info('finally for run')
        log.info('reached return for runStep')