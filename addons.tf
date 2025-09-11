# Install metrics-server using Helm
resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  namespace  = "kube-system"
  version    = "3.11.0"

  set {
    name  = "args[0]"
    value = "--cert-dir=/tmp"
  }

  set {
    name  = "args[1]"
    value = "--secure-port=4443"
  }

  set {
    name  = "args[2]"
    value = "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname"
  }

  set {
    name  = "args[3]"
    value = "--kubelet-use-node-status-port"
  }

  set {
    name  = "args[4]"
    value = "--metric-resolution=15s"
  }

  depends_on = [
    module.eks.eks_managed_node_groups,
    aws_eks_addon.vpc_cni,
    aws_eks_addon.coredns,
  ]
}

# Create a test namespace
resource "kubernetes_namespace" "test" {
  metadata {
    name = "test"
    labels = {
      name = "test"
    }
  }

  depends_on = [
    module.eks.eks_managed_node_groups,
  ]
}

# Test deployment to verify cluster functionality and internet access
resource "kubernetes_deployment" "test_app" {
  metadata {
    name      = "test-internet-app"
    namespace = kubernetes_namespace.test.metadata[0].name
    labels = {
      app = "test-internet-app"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "test-internet-app"
      }
    }

    template {
      metadata {
        labels = {
          app = "test-internet-app"
        }
      }

      spec {
        container {
          image = "alpine:latest"
          name  = "test-container"

          command = ["/bin/sh"]
          args    = ["-c", "while true; do wget -qO- http://httpbin.org/ip && echo ' - Internet access verified' && sleep 30; done"]

          resources {
            limits = {
              cpu    = "100m"
              memory = "128Mi"
            }
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
          }
        }
      }
    }
  }

  depends_on = [
    module.eks.eks_managed_node_groups,
    helm_release.metrics_server,
  ]
}