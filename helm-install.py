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

deployStages = ["uninstall","install","expose", "cleanup"]
deployOverride = dict()
deployOverride["expose"] = "expose"
deployOverride["cleanup"] = "cleanup"

def represent_dictionary_order(self, dict_data):
    return self.represent_mapping('tag:yaml.org,2002:map', dict_data.items())

def setup_yaml():
    yaml.add_representer(OrderedDict, represent_dictionary_order)

setup_yaml() 

try:
    with open('repositories.yaml', 'r') as stream:
        reps = yaml.safe_load(stream)
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
        script.append("helm repo add " + rep['label'] + " " + rep["url"])
    script.append("helm repo update")
    return script

def buildDeployStage(stage,install, name,app,namespace,repo,version, valExists):
    valOverride = ""
    if valExists:
        valOverride = " -f " + "./values/"+ name+".yaml"
    
    if install:
        cmd = "helm upgrade --install --namespace " + namespace + " " + namespace + "-" + name + " " + repo + "/" + app + " --version " + version +  valOverride
    else:
        cmd = "helm delete --purge "  + namespace + "-" + name
        
    script = []
    script.append("echo 'Upgrading " + name + " using " + app + "'")
    script.append(cmd)
        
    
    env = dict()
    env['name'] = namespace
    env['url'] = "https://knight.livspace.com"

    only= []
    only.append(branch)
    
    dep = dict()
    dep['stage'] = stage
    dep['script'] = script
    dep['only'] = only
    dep['environment'] = env
    return dep
    
gitlabci = OrderedDict()
gitlabci['image'] = "livspaceeng/python-helm"

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
    with open('cicd.yaml', 'w') as outfile:
        yaml.dump(gitlabci, outfile, default_flow_style=False)
else:
    raise Exception("there is nothing to upgrade nor to delete")
