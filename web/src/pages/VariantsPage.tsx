import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Card, Form, Input, message, Modal, Popconfirm, Space, Table, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { Variant } from '../api/types'

export default function VariantsPage() {
  const [items, setItems] = useState<Variant[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get<Variant[]>('/admin/variants')
      setItems(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const onCreate = async (values: { title: string }) => {
    await api.post('/admin/variants', values)
    message.success('Вариант создан')
    setCreateOpen(false)
    createForm.resetFields()
    load()
  }

  const toggleActive = async (id: number, active: boolean) => {
    await api.patch(`/admin/variants/${id}`, { is_active: active })
    message.success(active ? 'Вариант активирован' : 'Вариант деактивирован')
    load()
  }

  const archive = async (id: number) => {
    await api.post(`/admin/variants/${id}/archive`)
    message.success('Вариант архивирован')
    load()
  }

  const unarchive = async (id: number) => {
    await api.post(`/admin/variants/${id}/unarchive`)
    message.success('Вариант восстановлен (неактивен)')
    load()
  }

  return (
    <Card
      title="Варианты"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Новый вариант
        </Button>
      }
    >
      <Table<Variant>
        rowKey="id"
        loading={loading}
        pagination={false}
        dataSource={items}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: 'Название', dataIndex: 'title' },
          {
            title: 'Статус',
            key: 'status',
            width: 150,
            render: (_v, r) => {
              if (r.archived_at) return <Tag color="default">архивный</Tag>
              return r.is_active ? <Tag color="success">активный</Tag> : <Tag color="warning">неактивный</Tag>
            },
          },
          { title: 'Заданий', dataIndex: 'tasks_count', width: 100 },
          { title: 'Попыток', dataIndex: 'attempts_count', width: 100 },
                    {
            title: 'Действия',
            key: 'actions',
            width: 320,
            render: (_v, r) => (
              <Space>
                <Link to={`/variants/${r.id}`}>открыть</Link>
                {!r.archived_at ? (
                  <>
                    <Popconfirm
                      title={r.is_active ? 'деактивировать вариант?' : 'активировать вариант?'}
                      onConfirm={() => toggleActive(r.id, !r.is_active)}
                    >
                      <a>{r.is_active ? 'деактивировать' : 'активировать'}</a>
                    </Popconfirm>
                    <Popconfirm title="архивировать вариант?" onConfirm={() => archive(r.id)}>
                      <a>архивировать</a>
                    </Popconfirm>
                  </>
                ) : (
                  <Popconfirm
                    title="восстановить вариант? он станет неактивным"
                    onConfirm={() => unarchive(r.id)}
                  >
                    <a>восстановить</a>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title="Новый вариант"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => createForm.submit()}
        okText="Создать"
      >
        <Form form={createForm} layout="vertical" onFinish={onCreate}>
          <Form.Item name="title" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}