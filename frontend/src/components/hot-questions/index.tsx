import useSendMessage from '@/utils/useSendMessage'
import { debounce } from 'throttle-debounce'
import styles from './index.module.scss'

interface HotQuestion {
  emoji: string
  title: string
}

interface HotQuestionsProps {
  list?: HotQuestion[]
}

const list: HotQuestion[] = [
  {
    emoji: '🔬',
    title: 'PVA纤维掺量对EGC抗压强度有什么影响？',
  },
  {
    emoji: '📐',
    title: '如何优化EGC的极限拉伸应变？',
  },
  {
    emoji: '🌡️',
    title: '不同养护温度下EGC力学性能如何变化？',
  },
  {
    emoji: '⚖️',
    title: '粉煤灰基与矿渣基EGC的性能对比',
  },
  {
    emoji: '💧',
    title: '水胶比对EGC应变硬化行为的影响',
  },
]

export default function HotQuestions(props: HotQuestionsProps) {
  console.log('props', props)

  const sendMessage = useSendMessage()
  // 使用防抖处理点击事件，300ms内只触发一次
  const handleClick = debounce(300, (question: HotQuestion) => {
    sendMessage(question.title)
  })

  return (
    <div className={styles.hotQuestions}>
      {list.map((question) => (
        <div
          key={question.title}
          className={styles.hotQuestion}
          onClick={() => handleClick(question)}
        >
          <span className={styles.emoji}>{question.emoji}</span>
          <span className={styles.title}>{question.title}</span>
        </div>
      ))}
    </div>
  )
}
