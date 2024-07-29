# my-sample-controller-and-operator-k8s
This is my sample controller and operator in k8s
Concept:
1. Api-watcher Controller will listen on Flask-app, every PUT event on Flask-app, controller will trigger update ( or create if Crds kind resources not exist) Crds kind resources InforZ
2. Controller watch InforZ resources and collect data from spec.data, spec.personal and spec.gitrepo
3. Controller base on value of spec.gitrepo will clone the repo and apply data of spec.data and spec.personal to Jinja2 template file in repo clonded ( one htlm file for configmap and one deployment yaml file for deployment)
4. Controller will create configmap and map it to deployment (in my sample is nginx-web-app)
5. If InforZ is deleted, controller also delete configmap and deployment.
