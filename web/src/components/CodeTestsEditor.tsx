import { useState } from 'react'
import {
  Button, Checkbox, Form, Input, Modal, Select, Space, Table, Tag, Typography, message,
} from 'antd'
import api from '../api/client'
import type { AdminCodeTest, CodeRunResult } from '../api/types'

interface Props {
  taskId: number
  tests: AdminCodeTest[]
  onChanged: () => void
}

const statusLabel: Record<string, { color: string; text: string }> = {
  passed: { color: 'success', text: 'пройден' },
  wrong_answer: { color: 'error', text: 'неверный ответ' },
  runtime_error: { color: 'error', text: 'ошибка выполнения' },
  timeout: { color: 'warning', text: 'превышено время' },
  compile_error: { color: 'error', text: 'ошибка компиляции' },
}

export default function CodeTestsEditor({ taskId, tests, onChanged }: Props) {
  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<AdminCodeTest | null>(null)
  const [form] = Form.useForm()
  const [runOpen, setRunOpen] = useState(false)
  const [runForm] = Form.useForm()
  const [runResult, setRunResult] = useState<CodeRunResult | null>(null)
  const [busy, setBusy] = useState(false)

  const openCreate = () => {
    setEditing(null)
    form.setFieldsValue({
      name: `Тест ${tests.length + 1}`,
      stdin_text: '',
      expected_stdout_text: '',
      is_public: false,
      sort_order: tests.length + 1,
    })
    setEditOpen(true)
  }

  const openEdit = (t: AdminCodeTest) => {
    setEditing(t)
    form.setFieldsValue(t)
    setEditOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    try {
      if (editing) {
        await api.patch(`/admin/code-tests/${editing.id}`, values)
      } else {
        await api.post(`/admin/tasks/${taskId}/tests`, values)
      }
      message.success('Тест сохранён')
      setEditOpen(false)
      onChanged()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'Не удалось сохранить тест')
    }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/admin/code-tests/${id}`)
      onChanged()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'Не удалось удалить тест')
    }
  }

  const runReference = async () => {
    const values = await runForm.validateFields()
    setBusy(true)
    setRunResult(null)
    try {
      const { data } = await api.post<CodeRunResult>(
        `/admin/tasks/${taskId}/run-reference`,
        values,
      )
      setRunResult(data)
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'Прогон не выполнен')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ marginTop: 12 }}>
      <Space style={{ marginBottom: 8 }}>
        <Typography.Text strong>Тесты кода</Typography.Text>
        <Button size="small" onClick={openCreate}>Добавить тест</Button>
        <Button size="small" onClick={() => { setRunResult(null); setRunOpen(true) }}>
          Прогнать эталон
        </Button>
      </Space>

      <Table<AdminCodeTest>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={tests}
        columns={[
          { title: '№', dataIndex: 'sort_order', width: 50 },
          { title: 'Название', dataIndex: 'name', width: 150 },
          {
            title: 'Вход',
            dataIndex: 'stdin_text',
            render: (v: string) => <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{v}</pre>,
          },
          {
            title: 'Ожидаемый вывод',
            dataIndex: 'expected_stdout_text',
            render: (v: string) => <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{v}</pre>,
          },
          {
            title: 'Открытый',
            dataIndex: 'is_public',
            width: 90,
            render: (v: boolean) => (v ? <Tag color="blue">да</Tag> : <Tag>нет</Tag>),
          },
          {
            title: '',
            key: 'actions',
            width: 130,
            render: (_v, r) => (
              <Space>
                <a onClick={() => openEdit(r)}>изм.</a>
                <a onClick={() => remove(r.id)}>удал.</a>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? 'Изменить тест' : 'Новый тест'}
        open={editOpen}
        onOk={save}
        onCancel={() => setEditOpen(false)}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Название"><Input /></Form.Item>
          <Form.Item name="stdin_text" label="Входные данные (stdin)">
            <Input.TextArea rows={4} style={{ fontFamily: 'Consolas, monospace' }} />
          </Form.Item>
          <Form.Item name="expected_stdout_text" label="Ожидаемый вывод (stdout)">
            <Input.TextArea rows={4} style={{ fontFamily: 'Consolas, monospace' }} />
          </Form.Item>
          <Form.Item name="sort_order" label="Порядок"><Input type="number" /></Form.Item>
          <Form.Item name="is_public" valuePropName="checked" label="Открытый тест (виден ученику)">
            <Checkbox />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Прогон эталонного решения"
        open={runOpen}
        onOk={runReference}
        okButtonProps={{ loading: busy }}
        onCancel={() => setRunOpen(false)}
        width={760}
      >
        <Form form={runForm} layout="vertical" initialValues={{ language: 'python' }}>
          <Form.Item name="language" label="Язык">
            <Select
              options={[
                { value: 'python', label: 'Python' },
                { value: 'csharp', label: 'C#' },
              ]}
            />
          </Form.Item>
          <Form.Item name="source_code" label="Код эталонного решения" rules={[{ required: true }]}>
            <Input.TextArea rows={10} style={{ fontFamily: 'Consolas, monospace' }} />
          </Form.Item>
        </Form>

        {runResult && (
          <div>
            <Typography.Text strong>
              Итог: {runResult.all_passed ? 'все тесты пройдены' : 'не все тесты пройдены'}
            </Typography.Text>
            <Table
              rowKey="test_id"
              size="small"
              pagination={false}
              style={{ marginTop: 8 }}
              dataSource={runResult.tests}
              columns={[
                { title: 'Тест', dataIndex: 'name' },
                {
                  title: 'Статус',
                  dataIndex: 'status',
                  render: (s: string) => {
                    const m = statusLabel[s] ?? { color: 'default', text: s }
                    return <Tag color={m.color}>{m.text}</Tag>
                  },
                },
              ]}
            />
            {runResult.compile_log && (
              <>
                <Typography.Text type="danger">
                  Лог компиляции (виден только преподавателю):
                </Typography.Text>
                <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 8, maxHeight: 200, overflow: 'auto' }}>
                  {runResult.compile_log}
                </pre>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}