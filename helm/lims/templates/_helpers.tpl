{{/*
Common helpers — name, labels, full image refs.
*/}}

{{- define "lims.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "lims.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "lims.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lims.labels" -}}
app.kubernetes.io/name: {{ include "lims.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
lims.environment: {{ .Values.env }}
{{- end -}}

{{/*
componentLabels expects { root: <chart context>, component: <name> } so it
can call lims.labels with the real chart context (which has .Chart, .Release,
.Values) instead of the wrapping dict.
*/}}
{{- define "lims.componentLabels" -}}
{{ include "lims.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "lims.componentSelector" -}}
app.kubernetes.io/name: {{ include "lims.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/*
Image references. CI bumps `image.tag` in envs/<env>/values.yaml; we never
fall back to `latest` because Artifact Registry has immutable tags enabled.
*/}}
{{- define "lims.image.backend" -}}
{{- printf "%s/%s:%s" .Values.image.registry .Values.backend.image.repository (.Values.image.tag | required "image.tag is required (CI bumps it)") -}}
{{- end -}}

{{- define "lims.image.frontend" -}}
{{- printf "%s/%s:%s" .Values.image.registry .Values.frontend.image.repository (.Values.image.tag | required "image.tag is required (CI bumps it)") -}}
{{- end -}}

{{/*
Hash the rendered ConfigMap so changes trigger a rolling restart.
*/}}
{{- define "lims.configHash" -}}
{{- include (print $.Template.BasePath "/configmap.yaml") . | sha256sum -}}
{{- end -}}

{{/*
Pod-level securityContext shared across every workload.
*/}}
{{- define "lims.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "lims.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
runAsUser: 10001
capabilities:
  drop: ["ALL"]
{{- end -}}

{{/*
Pick the right ServiceAccount name. When .Values.serviceAccount.create is
false (e.g. local kind validation), pods fall back to the namespace's
"default" SA so they can still be admitted.
*/}}
{{- define "lims.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{ include "lims.fullname" . }}
{{- else -}}
default
{{- end -}}
{{- end -}}
