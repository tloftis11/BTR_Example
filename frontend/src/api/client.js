import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: BASE })

export const getSignalSites  = (params) => api.get('/api/signals/sites', { params }).then(r => r.data)
export const getTimeseries   = (params) => api.get('/api/signals/timeseries', { params }).then(r => r.data)
export const getVariants     = (params) => api.get('/api/signals/variants', { params }).then(r => r.data)
export const getSummary      = ()        => api.get('/api/signals/summary').then(r => r.data)
export const getAnomalies    = (params)  => api.get('/api/anomalies/', { params }).then(r => r.data)
export const triggerPipeline = ()        => api.post('/api/pipeline/run').then(r => r.data)
export const getPipelineRuns = ()        => api.get('/api/pipeline/runs').then(r => r.data)
export const getBriefing     = ()        => api.post('/api/chat/briefing').then(r => r.data)
export const sendChatMessage = (messages) => api.post('/api/chat/message', { messages }).then(r => r.data)
