import request from './request'
import type { ApiResponse, ShareCode, SharedKnowledgeBase, AccessLog } from '../types'

/** 生成分享码 */
export function generateShareCode(kbId: string, permission = 'read') {
  return request.post<ApiResponse<ShareCode>>(`/knowledge/bases/${kbId}/share-code`, { permission })
}

/** 吊销分享码 */
export function revokeShareCode(shareId: string) {
  return request.delete<ApiResponse<null>>(`/knowledge/share-codes/${shareId}`)
}

/** 列出知识库的所有分享码 */
export function listShareCodes(kbId: string) {
  return request.get<ApiResponse<ShareCode[]>>(`/knowledge/bases/${kbId}/share-codes`)
}

/** 凭分享码访问知识库 */
export function accessByShareCode(shareCode: string) {
  return request.post<ApiResponse<SharedKnowledgeBase>>('/knowledge/access-by-code', { share_code: shareCode })
}

/** 查询知识库的访问日志 */
export function listAccessLogs(kbId: string, page = 1, page_size = 20) {
  return request.get<ApiResponse<{ items: AccessLog[]; total: number; page: number; page_size: number }>>(
    `/knowledge/bases/${kbId}/access-logs`,
    { params: { page, page_size } },
  )
}
