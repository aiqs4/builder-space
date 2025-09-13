# Addons Module
# Deploys Kubernetes add-ons and applications to the EKS cluster

# Kubernetes provider configuration
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# Test deployment for internet connectivity verification
resource "kubernetes_namespace" "test" {
  count = var.enable_test_deployment ? 1 : 0
  metadata {
    name = "test"
    labels = {
      name    = "test"
      purpose = "connectivity-verification"
    }
  }
}

resource "kubernetes_deployment" "test_internet_app" {
  count = var.enable_test_deployment ? 1 : 0
  metadata {
    name      = "test-internet-app"
    namespace = kubernetes_namespace.test[0].metadata[0].name
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
          image = "curlimages/curl:latest"
          name  = "curl"

          command = [
            "/bin/sh",
            "-c",
            "while true; do echo 'Testing internet connectivity...'; curl -s https://httpbin.org/ip || echo 'Failed to reach internet'; sleep 30; done"
          ]

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

        restart_policy = "Always"
      }
    }
  }
}

# Metrics Server for resource monitoring (if enabled)
resource "helm_release" "metrics_server" {
  count      = var.enable_metrics_server ? 1 : 0
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  namespace  = "kube-system"
  version    = "3.12.1"

  set {
    name  = "args"
    value = "{--kubelet-insecure-tls,--kubelet-preferred-address-types=InternalIP\\,ExternalIP\\,Hostname}"
  }

  set {
    name  = "resources.requests.cpu"
    value = "50m"
  }

  set {
    name  = "resources.requests.memory"
    value = "128Mi"
  }

  set {
    name  = "resources.limits.cpu"
    value = "100m"
  }

  set {
    name  = "resources.limits.memory"
    value = "256Mi"
  }
}

# AWS Load Balancer Controller (if enabled for cost optimization)
resource "helm_release" "aws_load_balancer_controller" {
  count      = var.enable_aws_load_balancer_controller ? 1 : 0
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.8.2"

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "region"
    value = var.aws_region
  }

  set {
    name  = "vpcId"
    value = var.vpc_id
  }

  # Resource limits for cost optimization
  set {
    name  = "resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "resources.requests.memory"
    value = "128Mi"
  }

  set {
    name  = "resources.limits.cpu"
    value = "200m"
  }

  set {
    name  = "resources.limits.memory"
    value = "256Mi"
  }
}