#!/usr/bin/env python

import yaml
import sys
import hashlib
import os
import filecmp
import shutil
from collections import OrderedDict

pathToUpYaml = sys.argv[1]
pathToDelYaml = sys.argv[2]
pathToValYaml = sys.argv[3]
ns = sys.argv[4]
branch = sys.argv[5]

valuesDir = "values"
glEnvUrl = "https://knight.livspace.com"
glImage = "alpine/helm:2.11.0"
glCiYaml = "cicd.yaml"

if 'GL_IMAGE' in os.environ:
    glImage = os.environ['GL_IMAGE']
if 'GL_ENV_URL' in os.environ:
    glEnvUrl = os.environ['GL_IMAGE']
if 'GL_CI_YAML' in os.environ:
    glCiYaml = os.environ['GL_CI_YAML']
if 'VALUES_DIR' in os.environ:
    valuesDir = os.environ['VALUES_DIR']

deployStages = []
deployOverride = dict()

def represent_dictionary_order(self, dict_data):
    return self.represent_mapping('tag:yaml.org,2002:map', dict_data.items())

def setup_yaml():
    yaml.add_representer(OrderedDict, represent_dictionary_order)

setup_yaml() 

def repoMap(repoList):
    ret = dict()
    for k in repoList:
        ret[k['url']]= k
        if 'rewrite' in k:
            k['url'] = k['rewrite']
    return ret

try:
    with open('pipeline-config.yml', 'r') as stream:
        pipeConfig = yaml.safe_load(stream)
        reps = repoMap(pipeConfig['repositories'])
        if 'stages' in pipeConfig:
            deployStages = pipeConfig['stages']
        if 'apps-stage' in pipeConfig:
            deployOverride = pipeConfig['apps-stage']
except Exception as exc:
    print(exc)
    raise exc
    
try:
    with open(pathToUpYaml, 'r') as stream:
        ups = yaml.safe_load(stream)
        upYaml = ups['dependencies']
except Exception as exc:
    print(exc)
    upYaml = []
    
try:
    with open(pathToDelYaml, 'r') as stream:
        dels = yaml.safe_load(stream)
        delYaml = dels['dependencies']
except Exception as exc:
    print(exc)
    delYaml = []
    
def getrepo(repo):
    return reps[repo]["label"]
    
def beforeScript(repo):
    script = []
    script.append("helm init -c --tiller-namespace $TILLER_NAMESPACE")
    for k,rep in repo.items():
        script.append("helm repo add " + rep['label'] + " " + rep['url'])
    script.append("helm repo update")
    return script

def buildDeployStage(stage,install, name,app,namespace,repo,version, valExists):
    valOverride = ""
    if valExists:
        valOverride = " -f "  + valuesDir + "/"+ name+".yaml"
    
    if install:
        cmd = "helm upgrade --install --namespace " + namespace + " " + namespace + "-" + name + " " + repo + "/" + app + " --version " + version +  valOverride
    else:
        cmd = "helm delete --purge "  + namespace + "-" + name
        
    script = []
    script.append("echo 'Upgrading " + name + " using " + app + "'")
    script.append(cmd)
        
    
    env = dict()
    env['name'] = namespace
    env['url'] = glEnvUrl

    only= []
    only.append(branch)
    
    dep = dict()
    dep['stage'] = stage
    dep['script'] = script
    dep['only'] = only
    dep['environment'] = env
    return dep
    
gitlabci = OrderedDict()
gitlabci['image'] = glImage

gitlabci['before_script'] = beforeScript(reps)

gitlabci['stages'] = deployStages


done1 = False
done2 = False

for apps in delYaml:
    done2 = True
    deployName = apps['name']
    if 'alias' in apps:
        deployName = apps['alias']
        
    repo = getrepo(apps['repository'])
    valExists = os.path.isfile(pathToValYaml + "/" +deployName + ".yaml" )
    
    gitlabci[deployName] = buildDeployStage("uninstall", False, deployName, apps['name'], ns, repo, apps['version'], valExists)
    
    
for apps in upYaml:
    done1 =True
    deployName = apps['name']    
    if 'alias' in apps:
        deployName = apps['alias']
        
    deployTo = "install"
    if deployName in deployOverride:
        deployTo = deployOverride[deployName]
        
    repo = getrepo(apps['repository'])
    valExists = os.path.isfile(pathToValYaml + "/" +deployName + ".yaml" )
    
    gitlabci[deployName] = buildDeployStage(deployTo, True, deployName, apps['name'], ns, repo,apps['version'], valExists)
    


if done1 or done2:
    with open(glCiYaml, 'w') as outfile:
        yaml.dump(gitlabci, outfile, default_flow_style=False)
else:
    raise Exception("there is nothing to upgrade nor to delete")
