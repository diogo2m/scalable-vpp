# Scaling VPP environment

## Kubernetes installation
```bash
su root
```

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
```

```bash
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg
mkdir -p -m 755 /etc/apt/keyrings
```

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
```

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
sudo chmod 644 /etc/apt/sources.list.d/kubernetes.list
apt-get update
```

```bash
apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
apt-get install -y kubelet kubeadm kubectl
systemctl enable --now kubelet
systemctl enable --now docker.service
systemctl enable --now containerd.service
```

```bash
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
```

Disable swap immediately
```bash
sudo swapoff -a
```

Make it permanent (comment out swap line in /etc/fstab)
```bash
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

```bash
sudo swapon --show
# (should return nothing)
```

Add to `/etc/modules-load.d/containerd.conf`
```
overlay
br_netfilter
```

```bash
sudo modprobe overlay
sudo modprobe br_netfilter
```

Now in `/etc/sysctl.d/kubernetes.conf`
```
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
```

`/etc/default/kubelet`
```
KUBELET_EXTRA_ARGS="--node-ip=$IPADDR"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart kubelet
```

```bash
sudo containerd config default | sudo tee /etc/containerd/config.toml
```

`/etc/containerd/config.toml`
```
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
SystemdCgroup = true
```

`/etc/default/grub`
```bash
GRUB_CMDLINE_LINUX_DEFAULT="console=ttyS0,115200n8 iommu=1 intel_iommu=on enable_unsafe_noiommu_mode=1 vfio_iommu_type1.allow_unsafe_interrupts=1 default_hugepagesz=2048K hugepagesz=2048K hugepages=1024"
GRUB_CMDLINE_LINUX="iommu=pt iommu=1"
```

```bash
update-grub
sudo reboot
```

## Configuring cluster

Change the file and run:
```bash
kubeadm init --config cluster/cluster-config.yaml
```

```bash
export KUBECONFIG=/etc/kubernetes/admin.conf
```

```bash
mkdir -p ~/.kube
sudo cp /etc/kubernetes/admin.conf ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
```

```bash
kubectl taint nodes ${HOSTNAME} node-role.kubernetes.io/control-plane-
```

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.3/manifests/calico.yaml
```

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
helm install prometheus prometheus-community/prometheus -n monitoring --create-namespace
```

```bash
helm upgrade --install prometheus prometheus-community/prometheus -n monitoring --create-namespace \
  --set server.persistentVolume.enabled=true \
  --set server.persistentVolume.storageClass="local-path" \
  --set server.persistentVolume.size=5Gi \
  --set alertmanager.persistentVolume.enabled=true \
  --set alertmanager.persistentVolume.storageClass="local-path" \
  --set alertmanager.persistentVolume.size=2Gi
```

```bash
helm repo add kedacore https://kedacore.github.io/charts  
helm install keda kedacore/keda -n keda --create-namespace
```

```bash
cd vpp
docker build . -t vpp
docker image ls
docker save vpp -o vpp.tar
ctr -n k8s.io image import vpp.tar
ctr -n k8s.io image ls
cd ..
```

```bash
kubectl get configmap -n monitoring prometheus-server -o yaml > prom.yaml
```

Edit prom.yaml
```
    - job_name: 'vpp'
      static_configs:
        - targets: ['vpp-metrics.default.svc.cluster.local:9191']
```

```bash
kubectl apply -f prom.yaml
```

```bash
kubectl rollout restart deployment prometheus-server -n monitoring
```

```bash
kubectl apply -f vpp-metrics.yaml
kubectl apply -f keda.yaml
kubectl apply -f deployment.yaml
```

```bash
kubectl port-forward svc/prometheus-server 9090:80 -n monitoring --address 0.0.0.0
```
