import { useEffect } from 'react'
import { Button, Card, Form, Input, InputNumber, message, Typography } from 'antd'
import api from '../api/client'
import type { Settings } from '../api/types'

const MB = 1024 * 1024

export default function SettingsPage() {
  const [form] = Form.useForm()

  useEffect(() => {
    api.get<Settings>('/admin/settings')
      .then((r) => {
        form.setFieldsValue({
          exam_duration_minutes: r.data.exam_duration_minutes,
          instruction_text: r.data.instruction_text,
          max_file_size_mb: r.data.max_file_size_bytes / MB,
        })
      })
      .catch(() => message.error('Не удалось загрузить настройки'))
  }, [form])

  const onFinish = async (values: {
    exam_duration_minutes: number
    instruction_text: string
    max_file_size_mb: number
  }) => {
    try {
      await api.put('/admin/settings', {
        exam_duration_minutes: values.exam_duration_minutes,
        instruction_text: values.instruction_text,
        max_file_size_bytes: Math.round(values.max_file_size_mb * MB),
      })
      message.success('Настройки сохранены')
    } catch {
      message.error('Не удалось сохранить настройки')
    }
  }

  return (
    <Card title="Настройки системы" style={{ maxWidth: 800 }}>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item
          name="exam_duration_minutes"
          label="Длительность экзамена, минут"
          rules={[{ required: true, message: 'Укажите длительность' }]}
        >
          <InputNumber min={1} max={600} style={{ width: 200 }} />
        </Form.Item>

        <Form.Item
          name="max_file_size_mb"
          label="Максимальный размер файла задания, МБ"
          rules={[{ required: true, message: 'Укажите лимит' }]}
        >
          <InputNumber min={1} max={1024} style={{ width: 200 }} />
        </Form.Item>

        <Form.Item
          name="instruction_text"
          label={
            <Typography.Text>
              Инструкция для страницы 0 — показывается всем ученикам
            </Typography.Text>
          }
        >
          <Input.TextArea rows={12} />
        </Form.Item>

        <Button type="primary" htmlType="submit">Сохранить</Button>
      </Form>
    </Card>
  )
}