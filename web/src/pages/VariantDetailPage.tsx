import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { AdminField, AdminTask, VariantDetail } from '../api/types'

const scoringTypeOptions = [
  { value: 'all_or_nothing', label: 'Всё или ничего' },
  { value: 'partial_sum', label: 'Частичный балл (только задания 26 и 27)' },
]

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
  return `${(bytes / 1024).toFixed(1)} КБ`
}


function TaskEditorModal({
  open,
  variantId,
  task,
  onClose,
  onSaved,
}: {
  open: boolean
  variantId: number
  task: AdminTask | null
  onClose: () => void
  onSaved: () => void
}) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (!open) return
    if (task) {
      form.setFieldsValue({
        number: task.number,
        title: task.title,
        statement_text: task.statement_text,
        instruction_text: task.instruction_text,
        source_data_text: task.source_data_text,
        teacher_comment: task.teacher_comment,
        max_score: task.max_score,
        scoring_type: task.scoring_type,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({ max_score: 1, scoring_type: 'all_or_nothing' })
    }
  }, [open, task, form])

  const onFinish = async (values: Record<string, unknown>) => {
    try {
      if (task) {
        await api.patch(`/admin/tasks/${task.id}`, values)
      } else {
        await api.post(`/admin/variants/${variantId}/tasks`, values)
      }
      message.success('Задание сохранено')
      onSaved()
      onClose()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка сохранения задания')
    }
  }

  return (
    <Modal
      title={task ? `Редактирование задания №${task.number}` : 'Новое задание'}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="Сохранить"
      cancelText="Отмена"
      width={800}
    >
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Row gutter={16}>
          <Col span={4}>
            <Form.Item name="number" label="Номер" rules={[{ required: true, message: 'Укажите номер' }]}>
              <InputNumber min={1} max={27} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={20}>
            <Form.Item name="title" label="Заголовок" rules={[{ required: true, message: 'Укажите заголовок' }]}>
              <Input />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="statement_text" label="Текст задания">
          <Input.TextArea rows={4} />
        </Form.Item>
        <Form.Item name="instruction_text" label="Инструкция к заданию">
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item name="source_data_text" label="Исходные данные">
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item name="teacher_comment" label="Комментарий для преподавателя">
          <Input.TextArea rows={2} />
        </Form.Item>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="max_score" label="Максимальный балл">
              <InputNumber min={0} max={4} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={16}>
            <Form.Item name="scoring_type" label="Тип проверки">
              <Select options={scoringTypeOptions} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  )
}


function FieldEditorModal({
  open,
  task,
  field,
  onClose,
  onSaved,
}: {
  open: boolean
  task: AdminTask | null
  field: AdminField | null
  onClose: () => void
  onSaved: () => void
}) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (!open) return
    if (field) {
      form.setFieldsValue({
        code: field.code,
        label: field.label,
        input_type: field.input_type,
        sort_order: field.sort_order,
        points: field.points,
        expected_answer: field.expected_answer,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({ input_type: 'string', sort_order: 1, points: 1 })
    }
  }, [open, field, form])

  const onFinish = async (values: Record<string, unknown>) => {
    if (!task) return
    try {
      if (field) {
        await api.patch(`/admin/fields/${field.id}`, values)
      } else {
        await api.post(`/admin/tasks/${task.id}/fields`, values)
      }
      message.success('Поле сохранено')
      onSaved()
      onClose()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка сохранения поля')
    }
  }

  return (
    <Modal
      title={field ? `Редактирование поля «${field.label}»` : 'Новое поле ответа'}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="Сохранить"
      cancelText="Отмена"
    >
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="code" label="Код поля" rules={[{ required: true, message: 'Укажите код' }]}>
              <Input placeholder="answer, part1, cell_a1..." />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="label" label="Подпись" rules={[{ required: true, message: 'Укажите подпись' }]}>
              <Input />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={10}>
            <Form.Item name="input_type" label="Тип ввода">
              <Select
                options={[
                  { value: 'string', label: 'строка / последовательность' },
                  { value: 'number', label: 'число' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={7}>
            <Form.Item name="sort_order" label="Порядок">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={7}>
            <Form.Item name="points" label="Баллы за поле">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="expected_answer" label="Правильный ответ">
          <Input />
        </Form.Item>
      </Form>
    </Modal>
  )
}


export default function VariantDetailPage() {
  const { id } = useParams()
  const variantId = Number(id)

  const [variant, setVariant] = useState<VariantDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [taskModal, setTaskModal] = useState<{ open: boolean; task: AdminTask | null }>({
    open: false,
    task: null,
  })
  const [fieldModal, setFieldModal] = useState<{
    open: boolean
    task: AdminTask | null
    field: AdminField | null
  }>({ open: false, task: null, field: null })

  const load = async () => {
    try {
      const { data } = await api.get<VariantDetail>(`/admin/variants/${variantId}`)
      setVariant(data)
      setError(null)
    } catch {
      setError('Не удалось загрузить вариант')
    }
  }

  useEffect(() => {
    load()
  }, [variantId])

  const archiveTask = async (taskId: number) => {
    try {
      await api.post(`/admin/tasks/${taskId}/archive`)
      message.success('Задание архивировано')
      load()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка архивирования')
    }
  }

  const deleteField = async (fieldId: number) => {
    try {
      await api.delete(`/admin/fields/${fieldId}`)
      message.success('Поле удалено')
      load()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка удаления поля')
    }
  }

  const uploadFile = async (task: AdminTask, file: File) => {
    const form = new FormData()
    form.append('file', file)
    try {
      await api.post(`/admin/tasks/${task.id}/files`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      message.success('Файл загружен')
      load()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка загрузки файла')
    }
  }

  const deleteFile = async (fileId: number) => {
    try {
      await api.delete(`/admin/files/${fileId}`)
      message.success('Файл удалён')
      load()
    } catch (e: any) {
      message.error(e.response?.data?.detail ?? 'Ошибка удаления файла')
    }
  }

  if (error) return <Alert type="error" message={error} showIcon />
  if (!variant) return <div style={{ padding: 40 }}>Загрузка…</div>

  const variantEditable = !variant.archived_at

  return (
    <>
      <Card
        title={`Вариант: ${variant.title}`}
        extra={<Link to="/variants">← к списку вариантов</Link>}
      >
        <Space>
          <Tag color={variant.is_active ? 'success' : 'warning'}>
            {variant.is_active ? 'активный' : 'неактивный'}
          </Tag>
          {variant.archived_at && <Tag color="default">архивный</Tag>}
          <Typography.Text type="secondary">
            заданий: {variant.tasks_count} · попыток: {variant.attempts_count}
          </Typography.Text>
        </Space>
      </Card>

      <Card
        title="Задания"
        style={{ marginTop: 16 }}
        extra={
          variantEditable && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setTaskModal({ open: true, task: null })}
            >
              Добавить задание
            </Button>
          )
        }
      >
        {variant.tasks.length === 0 && (
          <Typography.Text type="secondary">Заданий пока нет.</Typography.Text>
        )}

        {variant.tasks.map((task) => {
          const taskEditable = variantEditable && !task.archived_at
          return (
            <Card
              key={task.id}
              size="small"
              style={{ marginBottom: 16 }}
              title={
                <Space wrap>
                  <Tag color="blue">№{task.number}</Tag>
                  <span>{task.title}</span>
                  <Tag>{task.max_score} б.</Tag>
                  <Tag color={task.scoring_type === 'partial_sum' ? 'geekblue' : 'default'}>
                    {task.scoring_type === 'partial_sum' ? 'частичный балл' : 'всё или ничего'}
                  </Tag>
                  {task.archived_at && <Tag color="default">архив</Tag>}
                </Space>
              }
              extra={
                taskEditable && (
                  <Space>
                    <a onClick={() => setTaskModal({ open: true, task })}>редактировать</a>
                    <Popconfirm title="Архивировать задание?" onConfirm={() => archiveTask(task.id)}>
                      <a>архивировать</a>
                    </Popconfirm>
                  </Space>
                )
              }
            >
              {task.statement_text && (
                <Typography.Paragraph type="secondary" style={{ whiteSpace: 'pre-wrap' }}>
                  {task.statement_text}
                </Typography.Paragraph>
              )}

              {/* Поля ответов */}
              <Typography.Text strong>Поля ответов:</Typography.Text>
              <Table<AdminField>
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={task.fields}
                style={{ marginTop: 8 }}
                columns={[
                  { title: 'Код', dataIndex: 'code', width: 120 },
                  { title: 'Подпись', dataIndex: 'label' },
                  {
                    title: 'Тип',
                    dataIndex: 'input_type',
                    width: 100,
                    render: (v: string) => (v === 'number' ? 'число' : 'строка'),
                  },
                  { title: 'Баллы', dataIndex: 'points', width: 80 },
                  { title: 'Правильный ответ', dataIndex: 'expected_answer' },
                  {
                    title: '',
                    key: 'actions',
                    width: 140,
                    render: (_v, f) =>
                      taskEditable && (
                        <Space>
                          <a onClick={() => setFieldModal({ open: true, task, field: f })}>ред.</a>
                          <Popconfirm title="Удалить поле?" onConfirm={() => deleteField(f.id)}>
                            <a>удалить</a>
                          </Popconfirm>
                        </Space>
                      ),
                  },
                ]}
              />
              {taskEditable && (
                <Button
                  size="small"
                  style={{ marginTop: 8 }}
                  onClick={() => setFieldModal({ open: true, task, field: null })}
                >
                  + Добавить поле
                </Button>
              )}

              {/* Файлы */}
              <div style={{ marginTop: 16 }}>
                <Typography.Text strong>Файлы:</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  {task.files.length === 0 && (
                    <Typography.Text type="secondary">нет файлов</Typography.Text>
                  )}
                  {task.files.map((f) => (
                    <div
                      key={f.id}
                      style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 4 }}
                    >
                      <a href={`/api/files/${f.id}`} target="_blank" rel="noreferrer">
                        {f.original_name}
                      </a>
                      <Typography.Text type="secondary">{formatSize(f.size_bytes)}</Typography.Text>
                      {taskEditable && (
                        <Popconfirm title="Удалить файл?" onConfirm={() => deleteFile(f.id)}>
                          <a>удалить</a>
                        </Popconfirm>
                      )}
                    </div>
                  ))}
                  {taskEditable && (
                    <Upload
                      showUploadList={false}
                      beforeUpload={(file) => {
                        uploadFile(task, file as File)
                        return false
                      }}
                    >
                      <Button icon={<UploadOutlined />} size="small" style={{ marginTop: 8 }}>
                        Загрузить файл
                      </Button>
                    </Upload>
                  )}
                </div>
              </div>
            </Card>
          )
        })}
      </Card>

      <TaskEditorModal
        open={taskModal.open}
        variantId={variantId}
        task={taskModal.task}
        onClose={() => setTaskModal({ open: false, task: null })}
        onSaved={load}
      />

      <FieldEditorModal
        open={fieldModal.open}
        task={fieldModal.task}
        field={fieldModal.field}
        onClose={() => setFieldModal({ open: false, task: null, field: null })}
        onSaved={load}
      />
    </>
  )
}