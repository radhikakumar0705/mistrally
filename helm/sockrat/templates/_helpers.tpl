{{/* Common labels */}}
{{- define "sockrat.labels" -}}
app.kubernetes.io/part-of: sockrat
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/* Labels for one component: include "sockrat.component" (list . "backend") */}}
{{- define "sockrat.component" -}}
{{- $root := index . 0 -}}
app.kubernetes.io/name: {{ index . 1 }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
{{- end }}

{{/* Image reference: include "sockrat.image" (list . "backend") */}}
{{- define "sockrat.image" -}}
{{- $root := index . 0 -}}
{{- $name := index $root.Values.images (index . 1) -}}
{{- $tag := default $root.Chart.AppVersion $root.Values.images.tag -}}
{{- if $root.Values.images.registry -}}
{{ $root.Values.images.registry }}/{{ $name }}:{{ $tag }}
{{- else -}}
{{ $name }}:{{ $tag }}
{{- end -}}
{{- end }}

{{/* One generated secret value: the explicit value, else the one already in the cluster, else a new random one */}}
{{- define "sockrat.secretValue" -}}
{{- $value := index . 0 -}}{{- $existing := index . 1 -}}{{- $key := index . 2 -}}
{{- if $value -}}{{ $value | b64enc }}{{- else if hasKey $existing $key -}}{{ index $existing $key }}{{- else -}}{{ randAlphaNum 40 | b64enc }}{{- end -}}
{{- end }}

{{- define "sockrat.secretName" -}}
{{- default "sockrat-secrets" .Values.secrets.existingSecret -}}
{{- end }}

{{/* Restricted pod security context shared by our own containers */}}
{{- define "sockrat.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities: { drop: ["ALL"] }
{{- end }}

{{/* Secret-backed environment shared by the API, worker and migration job */}}
{{- define "sockrat.backendSecretEnv" -}}
- name: DB_PASSWORD
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: MYSQL_PASSWORD } }
- name: SECRET_KEY
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: SECRET_KEY } }
- name: JWT_SECRET_KEY
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: JWT_SECRET_KEY } }
- name: SANDBOX_TOKEN
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: SANDBOX_TOKEN } }
- name: GOOGLE_CLIENT_ID
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: GOOGLE_CLIENT_ID, optional: true } }
- name: GOOGLE_CLIENT_SECRET
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: GOOGLE_CLIENT_SECRET, optional: true } }
- name: GROQ_API_KEY
  valueFrom: { secretKeyRef: { name: {{ include "sockrat.secretName" . }}, key: GROQ_API_KEY, optional: true } }
{{- end }}
