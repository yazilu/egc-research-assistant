import { AxiosRequestConfig } from 'axios'
import { request } from './request'

/** 力学性能预测 */
export function predict(
  params: API.MixDesign,
  options?: AxiosRequestConfig,
) {
  return request.post<API.PredictionResult>(
    '/predict/',
    params,
    {
      params: { user_id: '1' },
      ...options,
    },
  )
}

/** 配比优化 */
export function optimize(
  params: {
    target: API.OptimizationTarget
    constraints?: API.MixDesign
  },
  options?: AxiosRequestConfig,
) {
  return request.post<API.OptimizationResult>(
    '/optimize/',
    params,
    {
      params: { user_id: '1' },
      ...options,
    },
  )
}

/** 查询结构化实验数据 */
export function queryExperimentalData(
  params: {
    fiber_type?: string
    binder_type?: string
    compressive_strength_min?: number
    compressive_strength_max?: number
    ultimate_tensile_strain_min?: number
    ultimate_tensile_strain_max?: number
    limit?: number
    offset?: number
  },
  options?: AxiosRequestConfig,
) {
  return request.get<{
    total: number
    data: API.ExperimentalDataRow[]
  }>('/experimental_data/', {
    params,
    ...options,
  })
}

/** 获取论文元数据 */
export function getPaperMetadata(
  kbId: number,
  options?: AxiosRequestConfig,
) {
  return request.get<{
    id: number
    file_name: string
    paper_title?: string
    authors?: string
    journal?: string
    publication_year?: number
    doi?: string
    abstract?: string
    file_type?: string
    extraction_status?: string
  }>(`/paper_metadata/${kbId}`, options)
}

/** 重新提取论文元数据 */
export function reExtract(
  kbId: number,
  options?: AxiosRequestConfig,
) {
  return request.post<{ kb_id: number; status: string; message: string }>(
    `/re_extract/${kbId}`,
    undefined,
    options,
  )
}
