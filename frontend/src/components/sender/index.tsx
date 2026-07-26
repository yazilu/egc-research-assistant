import * as api from '@/api'
import IconFile from '@/assets/component/file.svg'
import IconSend from '@/components/icons/IconSend'
import { sessionActions, sessionState } from '@/store/session'
import {
  DatabaseOutlined,
  GlobalOutlined,
  LoadingOutlined,
  ReadOutlined,
} from '@ant-design/icons'
import { Button, Input, Space, Upload, UploadFile } from 'antd'
import classNames from 'classnames'
import { PropsWithChildren, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import './index.scss'

const SUPPORTED_ATTACHMENT_EXTS = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.md', '.markdown', '.csv', '.json', '.html', '.htm']
const SUPPORTED_ATTACHMENT_ACCEPT = SUPPORTED_ATTACHMENT_EXTS.join(',')

const IconFile2 = (
  <svg
    className="com-sender__file-icon"
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
    <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
    <path d="M10 9H8"></path>
    <path d="M16 13H8"></path>
    <path d="M16 17H8"></path>
  </svg>
)

export default function ComSender(
  props: PropsWithChildren<{
    className?: string
    loading?: boolean
    onSend?: (value: string, files: string[]) => void | Promise<void>
    onContract?: () => void
  }>,
) {
  const { className, onSend, onContract, loading, ...rest } = props
  const { id: sessionId } = useParams()
  const [value, setValue] = useState('')
  const [fileList, setFileList] = useState<
    (UploadFile & {
      loading?: boolean
    })[]
  >(() =>
    sessionId
      ? (sessionState.chatFiles[sessionId] || []).map((f) => ({
          uid: f.uid,
          name: f.name,
          url: f.url,
          status: 'done' as const,
        }))
      : [],
  )

  // 文件列表变化时同步到全局 store（按 session 隔离）
  const isRestoring = useRef(true)
  useEffect(() => {
    if (isRestoring.current) {
      isRestoring.current = false
      return
    }
    if (!sessionId) return
    sessionActions.setChatFiles(
      sessionId,
      fileList
        .filter((f) => f.url)
        .map((f) => ({ uid: f.uid, name: f.name, url: f.url! })),
    )
  }, [fileList, sessionId])

  const uploading = useMemo(() => {
    return fileList.some((file) => file.loading)
  }, [fileList])

  const session = useSnapshot(sessionState)
  const localSearchActive = session.useDeep || session.useLocalSearch

  async function send() {
    if (uploading) {
      window.$app.message.info('正在上传中，请耐心等待')
      return
    }
    if (loading) return
    const uploadedFiles = fileList.filter((item) => item.url)
    const message = value.trim() || (uploadedFiles.length ? '请分析附件内容' : '')
    if (!message) return
    await onSend?.(
      message,
      uploadedFiles.map((item) => item.url!),
    )
    setValue('')
  }

  function removeFile(uid: string) {
    setFileList((prev) => prev.filter((f) => f.uid !== uid))
  }

  async function upload(
    file: UploadFile & {
      loading?: boolean
    },
  ) {
    if (fileList.length >= 10) {
      window.$app.message.error('最多只能上传 10 个附件')
      return
    }

    // 文件大小限制 20MB
    const maxSize = 20 * 1024 * 1024
    if ((file.size ?? 0) > maxSize) {
      window.$app.message.error('文件大小不能超过 20MB')
      return
    }

    // 支持的文件类型
    const fileName = file.name?.toLowerCase() || ''
    const isAllowed = SUPPORTED_ATTACHMENT_EXTS.some((ext) => fileName.endsWith(ext))
    if (!isAllowed) {
      window.$app.message.error('不支持的文件格式，请上传 PDF/DOCX/XLSX/PPTX/TXT/Markdown/CSV/JSON/HTML 文件')
      return
    }

    file.loading = true

    setFileList((prev) => [...prev, file])

    try {
      const { data } = await api.session.uploadChatFile({ files: file as any })
      const chatFile = data?.files?.[0]
      file.url = chatFile?.text_content || ''

      window.$app.message.success(`${file.name} 上传成功`)
    } catch (error: any) {
      window.$app.message.error(error?.message || `${file.name} 上传失败`)
    } finally {
      file.loading = false
      setFileList((prev) => [...prev])
    }
  }

  return (
    <div className={classNames('com-sender', className)} {...rest}>
      {fileList.length ? (
        <div className="com-sender__files">
          {fileList.map((file) => (
            <div key={file.uid} className="com-sender__file">
              {file.type?.startsWith('image/') ? (
                <img className="com-sender__file-image" src={file.preview} />
              ) : (
                <>
                  {IconFile2}
                  <div className="com-sender__file-name" title={file.name}>
                    {file.name}
                  </div>
                </>
              )}
              <button
                className="com-sender__file-remove"
                onClick={() => removeFile(file.uid)}
                aria-label="移除附件"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : null}

      <div className="com-sender__main">
        <Input.TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="按 Enter 发送，Shift + Enter 换行"
          autoSize={{ minRows: 2 }}
          autoFocus
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
        />

        <div className="com-sender__actions">
          <Space className="com-sender__actions-left" size={12}>
            {
              <Upload
                accept={SUPPORTED_ATTACHMENT_ACCEPT}
                showUploadList={false}
                beforeUpload={(file) => {
                  upload(file)
                  return false
                }}
              >
                <Button
                  variant="text"
                  color="default"
                >
                  {uploading ? <LoadingOutlined /> : <img src={IconFile} />}
                  附件
                </Button>
              </Upload>
            }

            <Button
              color={session.useDeep ? 'primary' : 'default'}
              variant={session.useDeep ? 'filled' : 'outlined'}
              icon={<ReadOutlined />}
              onClick={() => sessionActions.setUseDeep(!session.useDeep)}
            >
              深度探索
            </Button>

            <Button
              color={localSearchActive ? 'primary' : 'default'}
              variant={localSearchActive ? 'filled' : 'outlined'}
              icon={<DatabaseOutlined />}
              disabled={session.useDeep}
              title={session.useDeep ? '深度探索会默认启用本地搜索' : undefined}
              onClick={() => sessionActions.setUseLocalSearch(!session.useLocalSearch)}
            >
              本地搜索
            </Button>

            <Button
              color={session.useWeb ? 'primary' : 'default'}
              variant={session.useWeb ? 'filled' : 'outlined'}
              icon={<GlobalOutlined />}
              onClick={() => sessionActions.setUseWeb(!session.useWeb)}
            >
              网络搜索
            </Button>
          </Space>

          <Space className="com-sender__actions-right" size={12}>
            <Button
              className="btn-send"
              color="primary"
              variant="filled"
              onClick={send}
              loading={loading}
              disabled={!value && !fileList.length}
              icon={<IconSend />}
            ></Button>
          </Space>
        </div>
      </div>

      {/* <div className="com-sender__footer">
        <Space></Space>
      </div> */}
    </div>
  )
}
