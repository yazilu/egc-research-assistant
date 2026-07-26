import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<{
    sessions: API.Session[]
  }>(`/get_sessions/`, {
    ...options,
    params,
    loading: false,
  })
}

export function detail(
  params: {
    session_id: string
  },
  options?: AxiosRequestConfig,
) {
  return request.get<
    {
      created_at: string
      message_id: string
      session_id: string
      user_question: string
      model_answer: string
      think?: string
      documents?: string
      recommended_questions?: string[]
    }[]
  >(`/get_messages/`, {
    ...options,
    params,
    loading: false,
  })
}

export function create(params?: {}, options?: AxiosRequestConfig) {
  return request.post<
    API.Result<{
      session_id: string
    }>
  >(`/create_session`, params, { loading: false, ...options })
}

export function chat(
  params: {
    id: string
    message: string
    local_search?: boolean
    web_search?: boolean
    deep_research?: boolean
    attachments?: string[]
  },
  options?: AxiosRequestConfig,
) {
  const { id, deep_research, ..._params } = params
  if (deep_research) {
    return request.post<ReadableStream>(
      '/deep_research/',
      {
        ..._params,
      },
      {
        headers: {
          Accept: 'text/event-stream',
        },
        responseType: 'stream',
        adapter: 'fetch',
        loading: false,
        params: {
          session_id: id,
        },
        ...options,
      },
    )
  }
  return request.post<ReadableStream>(
    '/ai_search/',
    {
      ..._params,
    },
    {
      headers: {
        Accept: 'text/event-stream',
      },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      params: {
        session_id: id,
      },
      ...options,
    },
  )
}

export function remove(
  session_id: string,
  options?: AxiosRequestConfig,
) {
  return request.delete<API.Result<null>>(`/delete_session/`, {
    params: { session_id },
    ...options,
  })
}

export function uploadChatFile(params: { files: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('files', params.files)
  return request.post<
    API.Result<{
      files: { file_name: string; text_content: string }[]
    }>
  >(`/upload_chat_file/`, form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    loading: false,
    ...options,
  })
}

export function upload(params: { files: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('files', params.files)
  return request.post<API.Result<{ file_id: string; url: string }>>(
    `/upload_files/`,
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      loading: false,
      ...options,
    },
  )
}
