import styles from './index.module.scss'

export default function HomeBanner() {
  return (
    <div className={styles.banner}>
      <div className={styles.content}>
        <h1 className={styles.title}>EGC 力学性能研究智能助手</h1>
        <p className={styles.subtitle}>
          基于学术论文知识库，预测 EGC 配比力学行为，提供优化建议
        </p>
      </div>
    </div>
  )
}
