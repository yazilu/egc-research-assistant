import { Button, Collapse, Form, Input, InputNumber, Select, Space } from 'antd'
import styles from './index.module.scss'

const BINDER_OPTIONS = [
  { label: '粉煤灰 (Fly Ash)', value: 'fly_ash' },
  { label: '矿渣 (Slag)', value: 'slag' },
  { label: '偏高岭土 (Metakaolin)', value: 'metakaolin' },
  { label: '粉煤灰+矿渣 (Blend)', value: 'blend' },
]

const FIBER_OPTIONS = [
  { label: 'PVA', value: 'PVA' },
  { label: 'PE', value: 'PE' },
  { label: 'PP', value: 'PP' },
  { label: '钢纤维 (Steel)', value: 'steel' },
  { label: '玄武岩纤维 (Basalt)', value: 'basalt' },
  { label: '混杂纤维 (Hybrid)', value: 'hybrid' },
]

const CURING_OPTIONS = [
  { label: '常温养护 (Ambient)', value: 'ambient' },
  { label: '热养护 (Heat)', value: 'heat' },
  { label: '蒸汽养护 (Steam)', value: 'steam' },
  { label: '水养护 (Water)', value: 'water' },
]

export interface MixDesignFormValues {
  binder_type?: string
  fly_ash_ratio?: number
  slag_ratio?: number
  metakaolin_ratio?: number
  water_binder_ratio?: number
  sand_binder_ratio?: number
  alkaline_activator_type?: string
  naoh_molarity?: number
  na2sio3_naoh_ratio?: number
  activator_modulus?: number
  fiber_type?: string
  fiber_content_vol?: number
  fiber_length?: number
  fiber_diameter?: number
  fiber_tensile_strength?: number
  fiber_elastic_modulus?: number
  curing_age_days?: number
  curing_temperature?: number
  curing_method?: string
}

interface MixDesignInputProps {
  onPredict?: (values: MixDesignFormValues) => void
  onOptimize?: (values: MixDesignFormValues) => void
  loading?: boolean
}

export default function MixDesignInput({
  onPredict,
  onOptimize,
  loading,
}: MixDesignInputProps) {
  const [form] = Form.useForm<MixDesignFormValues>()

  const handlePredict = () => {
    const values = form.getFieldsValue()
    onPredict?.(values)
  }

  const handleOptimize = () => {
    const values = form.getFieldsValue()
    onOptimize?.(values)
  }

  return (
    <div className={styles['mix-design-form']}>
      <p className={styles['form-tip']}>
        输入已知的配比参数，留空的字段将不参与预测
      </p>

      <Form form={form} layout="vertical" size="small">
        <Collapse
          defaultActiveKey={['binder', 'fiber']}
          items={[
            {
              key: 'binder',
              label: '胶凝材料与基体',
              children: (
                <>
                  <Form.Item name="binder_type" label="胶凝材料类型">
                    <Select options={BINDER_OPTIONS} allowClear placeholder="选择胶凝材料类型" />
                  </Form.Item>
                  <Space>
                    <Form.Item name="fly_ash_ratio" label="粉煤灰比例 (0-1)">
                      <InputNumber min={0} max={1} step={0.05} style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item name="slag_ratio" label="矿渣比例 (0-1)">
                      <InputNumber min={0} max={1} step={0.05} style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item name="metakaolin_ratio" label="偏高岭土比例 (0-1)">
                      <InputNumber min={0} max={1} step={0.05} style={{ width: 140 }} />
                    </Form.Item>
                  </Space>
                  <Space>
                    <Form.Item name="water_binder_ratio" label="水胶比">
                      <InputNumber min={0.1} max={0.8} step={0.01} style={{ width: 100 }} />
                    </Form.Item>
                    <Form.Item name="sand_binder_ratio" label="砂胶比">
                      <InputNumber min={0} max={5} step={0.1} style={{ width: 100 }} />
                    </Form.Item>
                  </Space>
                  <Form.Item name="alkaline_activator_type" label="碱激发剂类型">
                    <Input
                      style={{ width: 200 }}
                      placeholder="如 NaOH+Na2SiO3"
                    />
                  </Form.Item>
                  <Space>
                    <Form.Item name="naoh_molarity" label="NaOH浓度 (mol/L)">
                      <InputNumber min={0} max={20} step={0.5} style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item name="na2sio3_naoh_ratio" label="Na2SiO3/NaOH比">
                      <InputNumber min={0} max={5} step={0.1} style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item name="activator_modulus" label="激发剂模数">
                      <InputNumber min={0} max={3} step={0.1} style={{ width: 120 }} />
                    </Form.Item>
                  </Space>
                </>
              ),
            },
            {
              key: 'fiber',
              label: '纤维参数',
              children: (
                <>
                  <Form.Item name="fiber_type" label="纤维类型">
                    <Select options={FIBER_OPTIONS} allowClear placeholder="选择纤维类型" />
                  </Form.Item>
                  <Space>
                    <Form.Item name="fiber_content_vol" label="体积掺量 (%)">
                      <InputNumber min={0} max={10} step={0.1} style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item name="fiber_length" label="纤维长度 (mm)">
                      <InputNumber min={0} max={50} step={0.5} style={{ width: 130 }} />
                    </Form.Item>
                    <Form.Item name="fiber_diameter" label="纤维直径 (μm)">
                      <InputNumber min={0} max={200} step={1} style={{ width: 130 }} />
                    </Form.Item>
                  </Space>
                  <Space>
                    <Form.Item name="fiber_tensile_strength" label="纤维抗拉强度 (MPa)">
                      <InputNumber min={0} max={5000} step={10} style={{ width: 160 }} />
                    </Form.Item>
                    <Form.Item name="fiber_elastic_modulus" label="纤维弹性模量 (GPa)">
                      <InputNumber min={0} max={300} step={1} style={{ width: 160 }} />
                    </Form.Item>
                  </Space>
                </>
              ),
            },
            {
              key: 'curing',
              label: '养护条件',
              children: (
                <Space>
                  <Form.Item name="curing_age_days" label="养护龄期 (天)">
                    <InputNumber min={1} max={365} step={1} style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item name="curing_temperature" label="养护温度 (℃)">
                    <InputNumber min={0} max={200} step={1} style={{ width: 140 }} />
                  </Form.Item>
                  <Form.Item name="curing_method" label="养护方式">
                    <Select options={CURING_OPTIONS} allowClear style={{ width: 160 }} />
                  </Form.Item>
                </Space>
              ),
            },
          ]}
        />
      </Form>

      <div className={styles['submit-area']}>
        <Button onClick={handleOptimize} loading={loading}>
          配比优化
        </Button>
        <Button type="primary" onClick={handlePredict} loading={loading}>
          性能预测
        </Button>
      </div>
    </div>
  )
}
