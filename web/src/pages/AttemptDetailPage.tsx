import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Alert, Card, Col, Descriptions, Row, Spin, Statistic, Table, Tag, Typography } from 'antd'
import api from '../api/client'
import type { AttemptDetail, StudentAnswerView } from '../api/types'
import { formatDateTime, formatDuration } from '../utils/format'

const statusMeta: Record<string, { color: string; label: string }> = {
  in_progress: { color: 'processing', label: 'идёт' },
  finished: { color: 'success', label: 'завершена' },
  time_expired: { color: 'warning', label: 'время вышло' },
  aborted: { color: 'error', label: 'прервана' },
}

export default function AttemptDetailPage() {
  const { id } = useParams()
  const [data, setData] = useState<AttemptDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<AttemptDetail>(`/admin/attempts/${id}`)
      .then((r) => setData(r.data))
      .catch(() => setError('Не удалось загрузить попытку'))
  }, [id])

  if (error) return <Alert type="error" message={error} showIcon />
  if (!data) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />

  const meta = statusMeta[data.attempt.status] ?? { color: 'default', label: data.attempt.status }

  return (
    <>
      <Card
        title={`Попытка №${data.attempt.id}`}
        extra={<Link to="/attempts">← к списку попыток</Link>}
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Ученик">{data.student.full_name}</Descriptions.Item>
          <Descriptions.Item label="Школа">{data.student.school_name}</Descriptions.Item>
          <Descriptions.Item label="Вариант">{data.variant_title}</Descriptions.Item>
          <Descriptions.Item label="Статус"><Tag color={meta.color}>{meta.label}</Tag></Descriptions.Item>
          <Descriptions.Item label="Начало">{formatDateTime(data.attempt.started_at)}</Descriptions.Item>
          <Descriptions.Item label="Завершение">{formatDateTime(data.attempt.finished_at)}</Descriptions.Item>
          <Descriptions.Item label="Длительность">{formatDuration(data.attempt.duration_seconds)}</Descriptions.Item>
          <Descriptions.Item label="Компьютер">{data.attempt.machine_id ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Таблица перевода" span={2}>
            {data.conversion_table_name ?? 'не использована'}
          </Descriptions.Item>
        </Descriptions>

        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={6}>
            <Statistic
              title="Первичный балл"
              value={data.scores.primary_score ?? '—'}
              suffix={`/ ${data.scores.max_primary_score}`}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Тестовый балл"
              value={data.scores.test_score ?? '—'}
              suffix={data.scores.max_test_score != null ? `/ ${data.scores.max_test_score}` : undefined}
            />
          </Col>
        </Row>
      </Card>

      {data.tasks.map((task) => (
        <Card
          key={task.task_id}
          size="small"
          style={{ marginTop: 16 }}
          title={`Задание ${task.number}. ${task.title}`}
          extra={
            <Tag color={task.score === task.max_score ? 'success' : task.score > 0 ? 'warning' : 'default'}>
              {task.score} из {task.max_score}
            </Tag>
          }
        >
          <Table<StudentAnswerView>
            rowKey="field_id"
            size="small"
            pagination={false}
            dataSource={task.answers}
            columns={[
              { title: 'Поле', dataIndex: 'field_label' },
              {
                title: 'Ответ ученика',
                dataIndex: 'student_answer',
                render: (v: string) =>
                  v === '' ? <Typography.Text type="secondary">— нет ответа —</Typography.Text> : v,
              },
              { title: 'Правильный ответ', dataIndex: 'expected_answer' },
              {
                title: 'Верно',
                dataIndex: 'is_correct',
                width: 90,
                render: (v: boolean | null) =>
                  v ? <Tag color="success">да</Tag> : <Tag color="error">нет</Tag>,
              },
              { title: 'Балл', dataIndex: 'score', width: 80, render: (v: number | null) => v ?? 0 },
            ]}
          />
        </Card>
      ))}
    </>
  )
}