import { useEffect } from 'react'
import { Button, Card, Divider, Form, Input, InputNumber, message, Typography } from 'antd'
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
          python_executable: r.data.python_executable,
          csc_path: r.data.csc_path,
          code_time_limit_seconds: r.data.code_time_limit_seconds,
        })
      })
      .catch(() => message.error('Не удалось загрузить настройки'))
  }, [form])

  const onFinish = async (values: {
    exam_duration_minutes: number
    instruction_text: string
    max_file_size_mb: number
    python_executable?: string
    csc_path?: string
    code_time_limit_seconds: number
  }) => {
    try {
      await api.put('/admin/settings', {
        exam_duration_minutes: values.exam_duration_minutes,
        instruction_text: values.instruction_text,
        max_file_size_bytes: Math.round(values.max_file_size_mb * MB),
        python_executable: values.python_executable ?? '',
        csc_path: values.csc_path ?? '',
        code_time_limit_seconds: values.code_time_limit_seconds,
      })
      message.success('Настройки сохранены')
    } catch {
      message.error('Не удалось сохранить настройки')
    }
  }

  return (
    <Card title="Настройки системы" style={{ maxWidth: 860 }}>
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
          label={<Typography.Text>Инструкция для страницы 0</Typography.Text>}
        >
          <Input.TextArea rows={10} />
        </Form.Item>

        <Divider orientation="left">Программные задания</Divider>

        <Form.Item
          name="python_executable"
          label="Полный путь к python.exe на ЭТОМ сервере"
          extra={
            <Typography.Text type="secondary">
              Например: C:\Python314\python.exe или C:\Program Files\Python312\python.exe.
              Пусто - в режиме разработки используется python сервера; в упакованном exe
              без этого пути Python-тесты вернут «ошибка компиляции».
            </Typography.Text>
          }
        >
          <Input placeholder="C:\Python314\python.exe" allowClear />
        </Form.Item>

        <Form.Item
          name="csc_path"
          label="Путь к csc.exe (необязательно)"
          extra={
            <Typography.Text type="secondary">
              Пусто - автопоиск: csc в PATH, затем штатный csc .NET Framework.
              Укажите путь к csc.exe из Visual Studio, если нужен современный C#.
            </Typography.Text>
          }
        >
          <Input placeholder="оставьте пустым для автопоиска" allowClear />
        </Form.Item>

        <Form.Item
          name="code_time_limit_seconds"
          label="Таймаут одного теста кода, секунд"
          rules={[{ required: true, message: 'Укажите таймаут' }]}
        >
          <InputNumber min={1} max={120} style={{ width: 200 }} />
        </Form.Item>

        <Button type="primary" htmlType="submit">Сохранить</Button>
      </Form>
    </Card>
  )
}