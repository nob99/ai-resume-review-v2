# Monitoring and alerting configuration

# Uptime check for the application (will be configured when Cloud Run is deployed)
resource "google_monitoring_uptime_check_config" "app_uptime" {
  count        = var.environment == "prod" ? 1 : 0
  display_name = "AI Resume Review App - ${var.environment}"
  project      = var.project_id

  http_check {
    path           = "/health"
    port           = "443"
    use_ssl        = true
    validate_ssl   = true
    request_method = "GET"
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${var.project_id}.run.app" # Will be updated with actual URL
    }
  }

  timeout = "10s"
  period  = "60s"
}

# Alert policy for high error rate
resource "google_monitoring_alert_policy" "error_rate" {
  count        = var.environment != "dev" ? 1 : 0
  display_name = "High Error Rate - ${var.environment}"
  project      = var.project_id

  conditions {
    display_name = "Error rate exceeds 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
      
      trigger {
        count = 1
      }
    }
  }

  combiner = "OR"

  notification_channels = [google_monitoring_notification_channel.team_alerts.name]

  documentation {
    content = "The error rate for Cloud Run service has exceeded 5% for the last 5 minutes."
  }
}

# Dashboard for monitoring
resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "AI Resume Review - ${var.environment}"
    gridLayout = {
      widgets = [
        {
          title = "Request Count"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                }
              }
            }]
          }
        },
        {
          title = "Request Latency"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                }
              }
            }]
          }
        },
        {
          title = "Database Connections"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\""
                }
              }
            }]
          }
        }
      ]
    }
  })

  project = var.project_id
}