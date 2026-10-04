import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, Form, Input, Select, Space, Button, Table } from 'antd'
import api from '../api/client'
import type { AttemptListItem, AttemptsList, School, StudentWithAttempts, StudentsList } from '../api/types'
import { formatDateTime } from '../utils/format'

function StudentAttempts({ studentId }: { studentId: number }) {
  const [items, setItems] = useState<AttemptListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<AttemptsList>(`/admin/students/${studentId}/attempts`, { params: { per_page: 50 } })
      .then((r) => setItems(r.data.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [studentId])

  return (
    <Table<AttemptListItem>
      rowKey="id"
      size="small"
      loading={loading}
      pagination={false}
      dataSource={items}
      columns={[
        { title: 'ID', dataIndex: 'id', width: 60 },
        { title: 'Вариант', dataIndex: 'variant_title' },
        { title: 'Статус', dataIndex: 'status' },
        { title: 'Начало', dataIndex: 'started_at', render: formatDateTime },
        { title: 'Первичный', dataIndex: 'primary_score', render: (v: number | null) => v ?? '—' },
        { title: 'Тестовый', dataIndex: 'test_score', render: (v: number | null) => v ?? '—' },
        { title: '', key: 'a', width: 90, render: (_v, r) => <Link to={`/attempts/${r.id}`}>открыть</Link> },
      ]}
    />
  )
}

export default function StudentsPage() {
  const [form] = Form.useForm()
  const [items, setItems] = useState<StudentWithAttempts[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [filters, setFilters] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get<School[]>('/public/schools').then((r) => setSchools(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    let alive = true
    const load = async () => {
      setLoading(true)
      try {
        const { data } = await api.get<StudentsList>('/admin/students', {
          params: { page, per_page: perPage, ...filters },
        })
        if (!alive) return
        setItems(data.items)
        setTotal(data.pagination.total)
      } catch {
        // игнорируем сетевые сбои
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => { alive = false }
  }, [page, perPage, filters])

  return (
    <Card title="Ученики">
      <Form
        form={form}
        layout="inline"
        style={{ marginBottom: 16 }}
        onFinish={(values) => {
          const clean: Record<string, unknown> = {}
          Object.entries(values).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') clean[k] = v
          })
          setPage(1)
          setFilters(clean)
        }}
      >
        <Form.Item name="search">
          <Input placeholder="Поиск по ФИО" allowClear style={{ width: 220 }} />
        </Form.Item>
        <Form.Item name="school_id">
          <Select
            placeholder="Школа"
            allowClear
            style={{ width: 260 }}
            options={schools.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">Применить</Button>
            <Button onClick={() => { form.resetFields(); setFilters({}); setPage(1) }}>Сброс</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table<StudentWithAttempts>
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{
          current: page,
          pageSize: perPage,
          total,
          showSizeChanger: true,
          showTotal: (t) => `Всего учеников: ${t}`,
        }}
        onChange={(p) => { setPage(p.current ?? 1); setPerPage(p.pageSize ?? 20) }}
        expandable={{
          expandedRowRender: (record) => <StudentAttempts studentId={record.id} />,
          rowExpandable: () => true,
        }}
        columns={[
          { title: 'ФИО', dataIndex: 'full_name' },
          { title: 'Школа', dataIndex: 'school_name' },
          { title: 'Попыток', dataIndex: 'attempts_count', width: 100 },
          { title: 'Последняя попытка', dataIndex: 'last_attempt_at', render: formatDateTime },
          {
            title: 'Лучший первичный',
            dataIndex: 'best_primary_score',
            width: 150,
            render: (v: number | null) => v ?? '—',
          },
        ]}
      />
    </Card>
  )
}