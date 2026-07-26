import { proxy } from 'valtio'
import * as apiSession from '@/api/session'

export interface ChatFile {
  uid: string
  name: string
  url: string
}

const state = proxy({
  list: [] as API.Session[],
  useLocalSearch: true,
  useWeb: false,
  useDeep: false,
  usePrediction: false,
  loading: false,
  chatFiles: {} as Record<string, ChatFile[]>,
})

const actions = {
  setList(list: API.Session[]) {
    state.list = list
  },
  add(item: API.Session) {
    state.list.unshift(item)
  },
  setUseWeb(useWeb: boolean) {
    state.useWeb = useWeb
  },
  setUseLocalSearch(useLocalSearch: boolean) {
    state.useLocalSearch = useLocalSearch
  },
  setUseDeep(useDeep: boolean) {
    state.useDeep = useDeep
    if (useDeep) {
      state.useLocalSearch = true
    }
  },
  remove(session_id: string) {
    state.list = state.list.filter((s) => s.session_id !== session_id)
  },
  setChatFiles(sessionId: string, files: ChatFile[]) {
    state.chatFiles[sessionId] = files
  },
  clearChatFiles(sessionId: string) {
    delete state.chatFiles[sessionId]
  },
  async fetchList() {
    state.loading = true
    try {
      const res = await apiSession.list()
      if (res.data?.sessions) {
        state.list = res.data.sessions
      }
    } finally {
      state.loading = false
    }
  },
}

export const sessionState = state
export const sessionActions = actions
