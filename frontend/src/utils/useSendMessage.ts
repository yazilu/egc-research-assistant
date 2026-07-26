import { transportToChatEnter } from '@/pages/chat/shared'
import { sessionActions } from '@/store/session'
import { setPageTransport } from '@/utils'
import * as apiSession from '@/api/session'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'

export default function useSendMessage() {
  const navigate = useNavigate()

  return async (message: string) => {
    const res = await apiSession.create({ session_name: message })
    const session_id = res.data?.session_id
    if (!session_id) return

    sessionActions.add({
      session_id,
      session_name: message,
      created_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      updated_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    })
    setPageTransport(transportToChatEnter, {
      data: {
        message,
      },
    })
    navigate(`/chat/${session_id}`)
  }
}
