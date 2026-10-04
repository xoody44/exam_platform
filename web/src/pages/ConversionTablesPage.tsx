import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, InputNumber, message, Modal, Popconfirm,
  Space, Table, Tag,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { ConversionTable } from '../api/types'

function TableEditor({
  existing, onClose, onSaved,
}: {
  existing: ConversionTable | null
  onClose: () => void
  onSaved: () => void
}) {
  const [form] = Form.useForm()
  const [entries, setEntries] = useState<Array<{ primary_score: number; test_score: number }>>([])

  useEffect(() => {
    if (existing) {
      form.setFieldsValue({
        name: existing.name,
        year: existing.year,
        max_primary: existing.max_primary,
      })
      setEntries(existing.entries.map((e) => ({ primary_score: e.primary_score, test_score: e.test_score })))
    } else {
      form.resetFields()
      setEntries([])
    }
  }, [existing, form])

  const addEntry = () => setEntries([...entries, { primary_score: 0, test_score: 0 }])
  const removeEntry = (idx: number) => setEntries(entries.filter((_, i) => i !== idx))
  const updateEntry = (idx: number, key: 'primary_score' | 'test_score', value: number) => {
    setEntries(entries.map((e, i) => (i === idx ? { ...e, [key]: value } : e)))
  }

  const onFinish = async (values: any) => {
    try {
      const payload = { ...values, entries }
      if (existing) {
        await api.patch(`/admin/conversion-tables/${existing.id}`, payload)
      } else {
        await api.post('/admin/conversion-tables', payload)
      }
      message.success('Сохранено')
      onSaved()
      onClose()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка')
    }
  }

  return (
    <Form form={form} layout="vertical" onFinish={onFinish}>
      <Form.Item name="name" label="Название" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Space>
        <Form.Item name="year" label="Год">
          <InputNumber />
        </Form.Item>
        <Form.Item name="max_primary" label="Макс. первичный балл" rules={[{ required: true }]}>
          <InputNumber min={1} max={100} />
        </Form.Item>
      </Space>

      <div style={{ marginBottom: 8, fontWeight: 600 }}>Строки таблицы</div>
      <Table
        rowKey={(_, idx) => String(idx)}
        size="small"
        pagination={false}
        dataSource={entries}
        columns={[
          {
            title: 'Первичный',
            dataIndex: 'primary_score',
            render: (v, _r, idx) => (
              <InputNumber
                min={0}
                value={v}
                onChange={(val) => updateEntry(idx, 'primary_score', val ?? 0)}
              />
            ),
          },
          {
            title: 'Тестовый',
            dataIndex: 'test_score',
            render: (v, _r, idx) => (
              <InputNumber
                min={0}
                max={100}
                value={v}
                onChange={(val) => updateEntry(idx, 'test_score', val ?? 0)}
              />
            ),
          },
          {
            title: '',
            key: 'a',
            width: 80,
            render: (_v, _r, idx) => <a onClick={() => removeEntry(idx)}>удалить</a>,
          },
        ]}
      />
      <Button size="small" style={{ marginTop: 8 }} onClick={addEntry}>
        + Добавить строку
      </Button>
      <div style={{ marginTop: 16 }}>
        <Button type="primary" htmlType="submit">Сохранить таблицу</Button>
      </div>
    </Form>
  )
}

export default function ConversionTablesPage() {
  const [items, setItems] = useState<ConversionTable[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<ConversionTable | null | 'new'>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get<ConversionTable[]>('/admin/conversion-tables')
      setItems(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const activate = async (id: number) => {
    await api.post(`/admin/conversion-tables/${id}/activate`)
    message.success('Таблица активирована')
    load()
  }

  return (
    <Card
      title="Таблицы перевода баллов"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>
          Новая таблица
        </Button>
      }
    >
      <Table<ConversionTable>
        rowKey="id"
        loading={loading}
        pagination={false}
        dataSource={items}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: 'Название', dataIndex: 'name' },
          { title: 'Год', dataIndex: 'year' },
          { title: 'Макс. первичный', dataIndex: 'max_primary', width: 140 },
          {
            title: 'Статус',
            key: 'status',
            width: 150,
            render: (_v, r) =>
              r.is_active ? <Tag color="success">активная</Tag> : <Tag>неактивная</Tag>,
          },
          {
            title: 'Строк',
            key: 'count',
            width: 80,
            render: (_v, r) => r.entries.length,
          },
          {
            title: 'Действия',
            key: 'actions',
            width: 250,
            render: (_v, r) => (
              <Space>
                <a onClick={() => setEditing(r)}>редактировать</a>
                {!r.is_active && (
                  <Popconfirm title="Сделать активной?" onConfirm={() => activate(r.id)}>
                    <a>активировать</a>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing === 'new' ? 'Новая таблица перевода' : 'Редактирование таблицы'}
        open={editing !== null}
        onCancel={() => setEditing(null)}
        footer={null}
        width={700}
      >
        <TableEditor
          existing={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={load}
        />
      </Modal>
    </Card>
  )
}