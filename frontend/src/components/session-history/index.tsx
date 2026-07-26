import * as apiSession from '@/api/session'
import { sessionActions, sessionState } from '@/store/session'
import { DeleteOutlined } from '@ant-design/icons'
import { useMount } from 'ahooks'
import dayjs from 'dayjs'
import { useCallback } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import styles from './index.module.scss'

export default function SessionHistory() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { list, loading } = useSnapshot(sessionState)

  useMount(() => {
    sessionActions.fetchList()
  })

  const handleDelete = useCallback(
    async (e: React.MouseEvent, sessionId: string) => {
      e.preventDefault()
      e.stopPropagation()
      try {
        await apiSession.remove(sessionId)
        sessionActions.remove(sessionId)
        window.$app.message.success('已删除')
        // 如果删除的是当前正在查看的会话，跳回首页
        if (id === sessionId) {
          navigate('/')
        }
      } catch {
        window.$app.message.error('删除失败')
      }
    },
    [id, navigate],
  )

  if (loading) {
    return <div className={styles.loading}>加载中...</div>
  }

  if (!list.length) {
    return (
      <div className={styles.empty}>
        <p>还没有对话记录</p>
        <p className={styles.hint}>点击"新对话"开始提问</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {list.map((item) => (
        <Link
          key={item.session_id}
          to={`/chat/${item.session_id}`}
          className={`${styles.item} ${id === item.session_id ? styles.active : ''}`}
        >
          <div className={styles.itemContent}>
            <span className={styles.name}>{item.session_name}</span>
            <span className={styles.time}>
              {dayjs(item.updated_at).format('MM-DD HH:mm')}
            </span>
          </div>
          <span
            className={styles.deleteBtn}
            onClick={(e) => handleDelete(e, item.session_id)}
            title="删除会话"
          >
            <DeleteOutlined />
          </span>
        </Link>
      ))}
    </div>
  )
}
