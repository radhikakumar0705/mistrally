{{/* Common labels */}}
{{- define "mistrally.labels" -}}
app.kubernetes.io/part-of: mistrally
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/* Labels for one component: include "mistrally.component" (list . "backend") */}}
{{- define "mistrally.component" -}}
{{- $root := index . 0 -}}
app.kubernetes.io/name: {{ index . 1 }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
{{- end }}

{{/* Image reference: include "mistrally.image" (list . "backend") */}}
{{- define "mistrally.image" -}}
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
{{- define "mistrally.secretValue" -}}
{{- $value := index . 0 -}}{{- $existing := index . 1 -}}{{- $key := index . 2 -}}
{{- if $value -}}{{ $value | b64enc }}{{- else if hasKey $existing $key -}}{{ index $existing $key }}{{- else -}}{{ randAlphaNum 40 | b64enc }}{{- end -}}
{{- end }}

{{- define "mistrally.secretName" -}}
{{- default "mistrally-secrets" .Values.secrets.existingSecret -}}
{{- end }}

{{/* Restricted pod security context shared by our own containers */}}
{{- define "mistrally.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities: { drop: ["ALL"] }
{{- end }}

{{/* Secret-backed environment shared by the API, worker and migration job */}}
{{- define "mistrally.backendSecretEnv" -}}
- name: DB_PASSWORD
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: MYSQL_PASSWORD } }
- name: SECRET_KEY
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: SECRET_KEY } }
- name: JWT_SECRET_KEY
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: JWT_SECRET_KEY } }
- name: SANDBOX_TOKEN
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: SANDBOX_TOKEN } }
- name: GOOGLE_CLIENT_ID
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: GOOGLE_CLIENT_ID, optional: true } }
- name: GOOGLE_CLIENT_SECRET
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: GOOGLE_CLIENT_SECRET, optional: true } }
- name: GROQ_API_KEY
  valueFrom: { secretKeyRef: { name: {{ include "mistrally.secretName" . }}, key: GROQ_API_KEY, optional: true } }
{{- end }}
