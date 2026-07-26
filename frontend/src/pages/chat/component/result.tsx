import IconAnswer from '@/assets/chat/answer.svg'
import IconCopy from '@/assets/chat/copy.svg'
import IconImage from '@/assets/chat/image.svg'
import IconLike from '@/assets/chat/like.svg'
import IconPlay from '@/assets/chat/play.svg'
import IconRefresh from '@/assets/chat/refresh.svg'
import IconRelated from '@/assets/chat/related.svg'
import IconRemove from '@/assets/chat/remove.svg'
import IconShare from '@/assets/chat/share.svg'
import IconSource from '@/assets/chat/source.svg'
import IconVideo from '@/assets/chat/video.svg'
import Markdown from '@/components/markdown'
import PredictionResult from '@/components/prediction-result'
import { PlusOutlined } from '@ant-design/icons'
import { Button, Dropdown } from 'antd'
import classNames from 'classnames'
import { TokenizerAndRendererExtension } from 'marked'
import { useMemo } from 'react'
import styles from './result.module.scss'

const Section = (props: {
  title: string
  icon: string
  children: React.ReactNode
}) => {
  return (
    <div className={styles['chat-message-result-section']}>
      <div className={styles['chat-message-result-section__title']}>
        <img className={styles.icon} src={props.icon} />
        <span className={styles.title}>{props.title}</span>
      </div>
      {props.children}
    </div>
  )
}

const CITATION_PATTERN = /##(\d+)\$\$/g

const MOJIBAKE_MARKERS = ['Ã', 'Â', 'â', 'ä¸', 'æ', 'ç', 'è', 'é', 'ï¼', '�']

const MOJIBAKE_REPLACEMENTS: Record<string, string> = {
  '\u00e2\u20ac\u0153': '"',
  '\u00e2\u0080\u009c': '"',
  '\u00e2\u20ac\u009d': '"',
  '\u00e2\u0080\u009d': '"',
  '\u00e2\u20ac\u02dc': "'",
  '\u00e2\u0080\u0098': "'",
  '\u00e2\u20ac\u2122': "'",
  '\u00e2\u0080\u0099': "'",
  '\u00e2\u20ac\u201c': '-',
  '\u00e2\u0080\u0093': '-',
  '\u00e2\u20ac\u201d': '-',
  '\u00e2\u0080\u0094': '-',
  '\u00e2\u20ac\u00a6': '...',
  '\u00e2\u0080\u00a6': '...',
  '\u00c2\u00b7': '·',
  '\u00c2 ': ' ',
  '\u00c2': '',
  '\ufffd': '',
}

const CP1252_BYTES: Record<number, number> = {
  0x20ac: 0x80,
  0x201a: 0x82,
  0x0192: 0x83,
  0x201e: 0x84,
  0x2026: 0x85,
  0x2020: 0x86,
  0x2021: 0x87,
  0x02c6: 0x88,
  0x2030: 0x89,
  0x0160: 0x8a,
  0x2039: 0x8b,
  0x0152: 0x8c,
  0x017d: 0x8e,
  0x2018: 0x91,
  0x2019: 0x92,
  0x201c: 0x93,
  0x201d: 0x94,
  0x2022: 0x95,
  0x2013: 0x96,
  0x2014: 0x97,
  0x02dc: 0x98,
  0x2122: 0x99,
  0x0161: 0x9a,
  0x203a: 0x9b,
  0x0153: 0x9c,
  0x017e: 0x9e,
  0x0178: 0x9f,
}

const mojibakeScore = (text: string) =>
  MOJIBAKE_MARKERS.reduce((score, marker) => score + text.split(marker).length - 1, 0)

const encodeAsMojibakeBytes = (text: string) => {
  const bytes: number[] = []
  for (const char of text) {
    const code = char.charCodeAt(0)
    if (code <= 0xff) {
      bytes.push(code)
      continue
    }
    const cp1252Byte = CP1252_BYTES[code]
    if (cp1252Byte === undefined) return null
    bytes.push(cp1252Byte)
  }
  return new Uint8Array(bytes)
}

const repairMojibake = (text: string) => {
  if (!MOJIBAKE_MARKERS.some((marker) => text.includes(marker))) return text
  const bytes = encodeAsMojibakeBytes(text)
  if (!bytes) return text
  const repaired = new TextDecoder('utf-8').decode(bytes)
  return mojibakeScore(repaired) < mojibakeScore(text) ? repaired : text
}

const cleanDisplayText = (value?: string) => {
  let text = repairMojibake(value || '')
  Object.entries(MOJIBAKE_REPLACEMENTS).forEach(([bad, good]) => {
    text = text.split(bad).join(good)
  })
  return text.replace(/\s+/g, ' ').trim()
}

const extractCitationIndexes = (text?: string) => {
  const indexes = new Set<number>()
  for (const match of text?.matchAll(CITATION_PATTERN) || []) {
    const index = Number(match[1])
    if (Number.isInteger(index) && index >= 0) indexes.add(index)
  }
  return indexes
}

const 答案 = (props: { item: API.ChatItem }) => {
  const { item } = props

  /* markdown */
  const extensions = useMemo<TokenizerAndRendererExtension[]>(
    () => [
      {
        name: 'reference',
        level: 'inline',
        start(src) {
          return src.match(/##\d+\$\$/)?.index
        },
        tokenizer(src) {
          const match = /^##(\d+?)\$\$/.exec(src)
          if (match) {
            const [raw, index] = match
            return {
              type: 'reference',
              raw,
              index: this.lexer.inlineTokens(index),
              tokens: [],
            }
          }
        },
        renderer(token) {
          const index = this.parser.parseInline(token.index)
          return `<span class="refrence-token" data-refrence-index="${index}">[${Number(index) + 1}]</span>`
        },
      },
    ],
    [],
  )

  return (
    <Section title="答案" icon={IconAnswer}>
      {item.think ? (
        <Markdown
          className={classNames(
            styles['chat-message-result__think'],
            styles['chat-message-result__md'],
          )}
          value={item.think}
          extensions={extensions}
        />
      ) : null}

      {item.content ? (
        <Markdown
          className={styles['chat-message-result__md']}
          value={item.content}
          extensions={extensions}
        />
      ) : null}

      {item.error ? (
        <div className={styles['chat-message-result__error']}>{item.error}</div>
      ) : null}
    </Section>
  )
}

const 来源 = (props: { item: API.ChatItem }) => {
  const { item } = props

  if (!item.reference?.length) return null

  const citedIndexes = extractCitationIndexes(item.content)
  if (!citedIndexes.size) return null

  const citedReferences = item.reference
    .map((ref, index) => ({ ref, index }))
    .filter(({ index }) => citedIndexes.has(index))

  if (!citedReferences.length) return null

  return (
    <Section title={`来源 (${citedReferences.length})`} icon={IconSource}>
      <div className={styles['chat-message-result__source']}>
        {citedReferences.map(({ ref, index }) => {
          const title = cleanDisplayText(ref.document_name) || (ref.url ? '网页' : '未知文档')
          const content = cleanDisplayText(ref.content_with_weight)
          return (
            <div key={ref.document_id || ref.url || index} className={styles.item}>
              <div className={styles.header}>
                <div className={styles.title}>
                  {index + 1}.{' '}
                  {ref.url ? (
                    <a href={ref.url} target="_blank" rel="noreferrer">
                      {title}
                    </a>
                  ) : (
                    title
                  )}
                </div>
              </div>
              {ref.url ? <div className={styles.url}>{ref.url}</div> : null}
              <div className={styles.content}>
                {content.slice(0, 300)}
                {content.length > 300 ? '...' : ''}
              </div>
            </div>
          )
        })}
      </div>
    </Section>
  )
}

const 笔记 = (props: { item: API.ChatItem }) => {
  const { item } = props
  console.log(item)

  // 后端暂未实现，使用假数据代替
  return (
    <Section title="笔记" icon={IconImage}>
      <div className={styles['chat-message-result__xhs']}>
        {Array.from({ length: 4 }).map((_) => (
          <div className={styles.item}>
            <div className={styles.header}>
              <img className={styles.cover} src={IconShare} />
            </div>

            <div className={styles.footer}>
              <div className={styles.title}>
                如何培养孩子的兴趣？家长学会这三点，孩子受益匪浅 - Classover
              </div>

              <div className={styles.user}>
                <img className={styles.avatar} src={IconShare} />
                <div className={styles.name}>Classover</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

const 图像 = (props: { item: API.ChatItem }) => {
  const { item } = props

  return (
    <Section title="图像" icon={IconImage}>
      <div className={styles['chat-message-result__images']}>
        {item.image_results?.images?.map((item, index) => (
          <div
            className={styles.item}
            key={index}
            onClick={() => window.open(item.link, '_blank')}
          >
            <div className={styles.box}>
              <img className={styles.cover} src={item.thumbnailUrl} />
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

const 视频 = (props: { item: API.ChatItem }) => {
  const { item } = props

  return (
    <Section title="视频" icon={IconVideo}>
      <div className={styles['chat-message-result__videos']}>
        {item.video_results?.videos?.map((item, index) => (
          <div
            className={styles.item}
            key={index}
            onClick={() => window.open(item.link, '_blank')}
          >
            <div className={styles.box}>
              <img className={styles.cover} src={item.imageUrl} />

              <img className={styles.play} src={IconPlay} />
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

const 相关 = (props: {
  item: API.ChatItem
  onSend?: (text: string) => void
}) => {
  const { item, onSend } = props

  if (
    !item.recommended_questions?.length ||
    item.recommended_questions.filter((q) => q).length === 0
  )
    return null

  return (
    <Section title="相关" icon={IconRelated}>
      <div className={styles['chat-message-result__quick-reply']}>
        {item.recommended_questions?.map((item, index) => (
          <div
            className={styles['item']}
            key={index}
            onClick={() => onSend?.(item)}
          >
            <span className={styles['text']}>
              {index + 1}．{item}
            </span>
            <PlusOutlined className={styles['arrow']} />
          </div>
        ))}
      </div>
    </Section>
  )
}

export function Result(props: {
  item: API.ChatItem
  isEnd?: boolean
  onSend?: (text: string) => void
}) {
  const { item, isEnd, onSend } = props

  const shareMenu = useMemo(() => {
    return [
      {
        key: 'pdf',
        label: 'Export as txt',
        onClick: async () => {
          const url = `data:text/plain;charset=utf-8,${encodeURIComponent(item.content ?? '')}`
          const a = document.createElement('a')
          a.href = url
          a.download = 'output.txt'
          a.click()
        },
      },
      {
        key: 'email',
        label: 'Send report via email',
      },
    ]
  }, [item.content])

  return (
    <div className={styles['chat-message-result']}>
      {item.think || item.content || item.error ? <答案 item={item} /> : null}

      {item.loading ? null : (
        <div className={styles['chat-message-result__actions']}>
          <Button variant="filled" color="default" shape="circle">
            <img src={IconCopy} />
          </Button>

          <Button variant="filled" color="default" shape="circle">
            <img src={IconRefresh} />
          </Button>

          <Button variant="filled" color="default" shape="circle">
            <img src={IconLike} />
          </Button>

          <Button variant="filled" color="default" shape="circle">
            <img src={IconRemove} />
          </Button>

          <Dropdown menu={{ items: shareMenu }}>
            <Button variant="filled" color="default" shape="circle">
              <img src={IconShare} />
            </Button>
          </Dropdown>
        </div>
      )}

      {item.reference?.length ? <来源 item={item} /> : null}

      {false ? <笔记 item={item} /> : null}

      {item.image_results?.images?.length ? <图像 item={item} /> : null}

      {item.video_results?.videos?.length ? <视频 item={item} /> : null}

      {item.prediction_result ? (
        <Section title="力学性能预测" icon={IconAnswer}>
          <PredictionResult data={item.prediction_result} />
        </Section>
      ) : null}

      {!item.loading && isEnd && item.recommended_questions?.length ? (
        <相关 item={item} onSend={onSend} />
      ) : null}
    </div>
  )
}
