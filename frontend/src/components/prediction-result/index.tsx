import classNames from 'classnames'
import styles from './index.module.scss'

interface PredictionResultProps {
  data?: API.PredictionResult
}

const PROPERTY_LABELS: Record<string, string> = {
  compressive_strength: '抗压强度',
  ultimate_tensile_strain: '极限拉伸应变',
  flexural_strength: '抗折强度',
  elastic_modulus: '弹性模量',
  tensile_strength: '抗拉强度',
  fracture_energy: '断裂能',
}

function ConfidenceBar({ confidence }: { confidence?: number }) {
  const pct = Math.round((confidence ?? 0) * 100)
  const level = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low'

  return (
    <>
      <div className={styles['confidence-bar']}>
        <div
          className={classNames(styles['fill'], styles[level])}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className={styles['confidence-label']}>置信度: {pct}%</div>
    </>
  )
}

export default function PredictionResult({ data }: PredictionResultProps) {
  if (!data || data.status === 'error') {
    return (
      <div className={styles['prediction-result']}>
        <div className={styles['section-title']}>预测结果</div>
        <p style={{ color: '#ff4d4f' }}>{data?.message || '预测失败'}</p>
      </div>
    )
  }

  const predictions = data.predictions
  if (!predictions) return null

  const hasAny = Object.values(predictions).some((p) => p?.value != null)

  return (
    <div className={styles['prediction-result']}>
      <div className={styles['section-title']}>
        力学性能预测
        {data.similar_data_count ? (
          <span style={{ fontWeight: 400, fontSize: 12, color: '#999', marginLeft: 8 }}>
            (基于 {data.similar_data_count} 组相似实验数据)
          </span>
        ) : null}
      </div>

      {hasAny ? (
        <div className={styles['property-grid']}>
          {Object.entries(predictions).map(([key, pred]) => {
            if (!pred || pred.value == null) return null
            return (
              <div key={key} className={styles['property-card']}>
                <div className={styles['property-name']}>
                  {PROPERTY_LABELS[key] || key}
                </div>
                <div className={styles['property-value']}>
                  {pred.value}
                  <span className={styles['unit']}>{pred.unit}</span>
                </div>
                {pred.range_low != null && pred.range_high != null ? (
                  <div className={styles['property-range']}>
                    范围: {pred.range_low} – {pred.range_high} {pred.unit}
                  </div>
                ) : null}
                <ConfidenceBar confidence={pred.confidence} />
              </div>
            )
          })}
        </div>
      ) : null}

      {data.strain_hardening_analysis ? (
        <div className={styles['sh-analysis']}>
          <strong>应变硬化评估: </strong>
          <span
            className={classNames(
              styles['sh-verdict'],
              data.strain_hardening_analysis.expected
                ? styles['expected']
                : styles['unlikely'],
            )}
          >
            {data.strain_hardening_analysis.expected ? '预计可应变硬化' : '可能难以应变硬化'}
          </span>
          <p style={{ marginTop: 8, fontSize: 13, color: '#666' }}>
            {data.strain_hardening_analysis.reasoning}
          </p>
        </div>
      ) : null}

      {data.key_findings ? (
        <div className={styles['key-findings']}>{data.key_findings}</div>
      ) : null}

      {data.limitations ? (
        <div className={styles['limitations']}>⚠ {data.limitations}</div>
      ) : null}
    </div>
  )
}
