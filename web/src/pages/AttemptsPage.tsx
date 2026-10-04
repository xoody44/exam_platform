import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, Select, Space, Table, Tag } from 'antd'
import type { TableProps } from 'antd'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { AttemptListItem, AttemptsList, Variant } from '../api/types'

const statusMeta: Record<string, { color: string; label: string }> = {
  in_progress: { color: 'processing', label: 'идёт' },
  finished: { color: 'success', label: 'завершена' },
  time_expired: { color: 'warning', label: 'время вышло' },
  aborted: { color: 'error', label: 'прервана' },
}

const sortKeyMap: Record<string, string> = {
  student_full_name: 'student_name',
  started_at: 'started_at',
  finished_at: 'finished_at',
  duration_seconds: 'duration_seconds',
  primary_score: 'primary_score',
  test_score: 'test_score',
  status: 'status',
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}ч ${m}м ${s}с`
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  // Сервер хранит наивное UTC-время: добавляем Z, чтобы браузер корректно конвертировал в локальное.
  const withZone = /([+-]\d{2}:\d{2}|Z)$/.test(iso) ? iso : `${iso}Z`
  return new Date(withZone).toLocaleString('ru-RU')
}

export default function AttemptsPage() {
  const [form] = Form.useForm()
  const [items, setItems] = useState<AttemptListItem[]>([])
  const [variants, setVariants] = useState<Variant[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [sortBy, setSortBy] = useState('started_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [filters, setFilters] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get<Variant[]>('/admin/variants').then((r) => setVariants(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    let alive = true
    const load = async () => {
      setLoading(true)
      try {
        const { data } = await api.get<AttemptsList>('/admin/attempts', {
          params: {
            page,
            per_page: perPage,
            sort_by: sortBy,
            sort_order: sortOrder,
            ...filters,
          },
        })
        if (!alive) return
        setItems(data.items)
        setTotal(data.pagination.total)
      } catch {
        // ошибка сети — показываем пустую таблицу, не роняем страницу
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [page, perPage, sortBy, sortOrder, filters])

  const columns: TableProps<AttemptListItem>['columns'] = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Ученик', dataIndex: 'student_full_name', sorter: true },
    { title: 'Школа', dataIndex: 'school_name' },
    { title: 'Вариант', dataIndex: 'variant_title' },
    {
      title: 'Статус',
      dataIndex: 'status',
      sorter: true,
      render: (status: string) => {
        const meta = statusMeta[status] ?? { color: 'default', label: status }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    { title: 'Начало', dataIndex: 'started_at', sorter: true, render: formatDateTime },
    { title: 'Завершение', dataIndex: 'finished_at', sorter: true, render: formatDateTime },
    { title: 'Длительность', dataIndex: 'duration_seconds', sorter: true, render: formatDuration },
    { title: 'Первичный', dataIndex: 'primary_score', sorter: true, render: (v: number | null) => v ?? '—' },
    { title: 'Тестовый', dataIndex: 'test_score', sorter: true, render: (v: number | null) => v ?? '—' },
    {
      title: '',
      key: 'action',
      width: 90,
      render: (_v, record) => <Link to={`/attempts/${record.id}`}>открыть</Link>,
    },
  ]

  const onTableChange: TableProps<AttemptListItem>['onChange'] = (pagination, _filters, sorter) => {
    setPage(pagination.current ?? 1)
    setPerPage(pagination.pageSize ?? 20)
    if (!Array.isArray(sorter) && sorter.field) {
      setSortBy(sortKeyMap[String(sorter.field)] ?? 'started_at')
      setSortOrder(sorter.order === 'ascend' ? 'asc' : 'desc')
    }
  }

  return (
    <Card title="Попытки">
      <Form
        form={form}
        layout="inline"
        style={{ marginBottom: 16, rowGap: 8 }}
        onFinish={(values) => {
          const clean: Record<string, unknown> = {}
          Object.entries(values).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') clean[key] = value
          })
          setPage(1)
          setFilters(clean)
        }}
      >
        <Form.Item name="search">
          <Input placeholder="Поиск по ФИО" allowClear style={{ width: 180 }} />
        </Form.Item>
        <Form.Item name="status">
          <Select
            placeholder="Статус"
            allowClear
            style={{ width: 160 }}
            options={Object.entries(statusMeta).map(([value, meta]) => ({ value, label: meta.label }))}
          />
        </Form.Item>
        <Form.Item name="variant_id">
          <Select
            placeholder="Вариант"
            allowClear
            style={{ width: 180 }}
            options={variants.map((v) => ({ value: v.id, label: v.title }))}
          />
        </Form.Item>
        <Form.Item name="min_primary"><InputNumber placeholder="Первичный от" /></Form.Item>
        <Form.Item name="max_primary"><InputNumber placeholder="до" /></Form.Item>
        <Form.Item name="min_test"><InputNumber placeholder="Тестовый от" /></Form.Item>
        <Form.Item name="max_test"><InputNumber placeholder="до" /></Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">Применить</Button>
            <Button onClick={() => { form.resetFields(); setFilters({}); setPage(1) }}>Сброс</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<AttemptListItem>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={items}
        onChange={onTableChange}
        pagination={{
          current: page,
          pageSize: perPage,
          total,
          showSizeChanger: true,
          showTotal: (t) => `Всего попыток: ${t}`,
        }}
      />
    </Card>
  )
}