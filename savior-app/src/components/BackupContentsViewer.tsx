import React, { useState, useEffect, useMemo } from 'react';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
  expanded?: boolean;
}

interface BackupContentsViewerProps {
  backupPath: string;
  projectName: string;
  onClose: () => void;
}

const BackupContentsViewer: React.FC<BackupContentsViewerProps> = ({ backupPath, projectName, onClose }) => {
  const [contents, setContents] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // File type icons mapping
  const getFileIcon = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    const iconMap: { [key: string]: string } = {
      // Code files
      'py': '🐍', 'js': '📜', 'ts': '💙', 'tsx': '⚛️', 'jsx': '⚛️',
      'java': '☕', 'cpp': '🔷', 'c': '🔷', 'cs': '🔶', 'go': '🐹',
      'rs': '🦀', 'php': '🐘', 'rb': '💎', 'swift': '🦉', 'kt': '🟣',

      // Web files
      'html': '🌐', 'css': '🎨', 'scss': '🎨', 'sass': '🎨', 'less': '🎨',

      // Data files
      'json': '📊', 'xml': '📄', 'yaml': '📝', 'yml': '📝', 'toml': '📝',
      'sql': '🗃️', 'db': '🗃️', 'sqlite': '🗃️',

      // Config files
      'env': '⚙️', 'config': '⚙️', 'ini': '⚙️', 'conf': '⚙️',

      // Docs
      'md': '📘', 'txt': '📄', 'pdf': '📕', 'doc': '📄', 'docx': '📄',

      // Images
      'png': '🖼️', 'jpg': '🖼️', 'jpeg': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
      'ico': '🖼️', 'webp': '🖼️',

      // Other
      'zip': '📦', 'tar': '📦', 'gz': '📦', 'rar': '📦',
      'exe': '⚙️', 'dmg': '💿', 'pkg': '📦', 'deb': '📦',
      'lock': '🔒', 'log': '📜', 'bak': '💾'
    };

    return iconMap[ext || ''] || '📄';
  };

  const getFolderIcon = (isExpanded: boolean): string => {
    return isExpanded ? '📂' : '📁';
  };

  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  useEffect(() => {
    loadBackupContents();
  }, [backupPath]);

  const loadBackupContents = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await (window as any).saviorAPI.getBackupContents({ backupPath });
      if (result.success) {
        setContents(result.contents);
      } else {
        setError(result.error || 'Failed to load backup contents');
      }
    } catch (err) {
      setError('Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const filterNodes = (node: FileNode, query: string): FileNode | null => {
    if (!query) return node;

    const matchesQuery = node.name.toLowerCase().includes(query.toLowerCase());

    if (node.type === 'file') {
      return matchesQuery ? node : null;
    }

    // For directories, include if name matches or any children match
    const filteredChildren = node.children
      ?.map(child => filterNodes(child, query))
      .filter(Boolean) as FileNode[] | undefined;

    if (matchesQuery || (filteredChildren && filteredChildren.length > 0)) {
      return {
        ...node,
        children: filteredChildren,
        expanded: true // Auto-expand folders with matches
      };
    }

    return null;
  };

  const FileTreeNode: React.FC<{ node: FileNode; depth: number }> = ({ node, depth }) => {
    const isExpanded = expandedPaths.has(node.path);
    const isSelected = selectedFile === node.path;

    return (
      <div>
        <div
          onClick={() => {
            if (node.type === 'directory') {
              toggleExpand(node.path);
            } else {
              setSelectedFile(node.path);
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '6px 12px',
            paddingLeft: `${12 + depth * 20}px`,
            cursor: 'pointer',
            userSelect: 'none',
            background: isSelected ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
            transition: 'all 0.15s ease',
            fontSize: '0.875rem',
            color: 'var(--text)'
          }}
          onMouseEnter={(e) => {
            if (!isSelected) {
              e.currentTarget.style.background = 'var(--hover-bg)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isSelected) {
              e.currentTarget.style.background = 'transparent';
            }
          }}
        >
          {/* Icon */}
          <span style={{
            marginRight: '8px',
            fontSize: '1rem',
            display: 'inline-flex',
            alignItems: 'center'
          }}>
            {node.type === 'directory'
              ? getFolderIcon(isExpanded)
              : getFileIcon(node.name)
            }
          </span>

          {/* Name */}
          <span style={{
            flex: 1,
            fontFamily: node.type === 'file' ? 'var(--mono)' : 'inherit',
            fontWeight: node.type === 'directory' ? 500 : 400,
            color: node.type === 'directory' ? 'var(--text-bright)' : 'var(--text)'
          }}>
            {node.name}
          </span>

          {/* Size or count */}
          {node.type === 'file' && node.size !== undefined && (
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              marginLeft: '12px'
            }}>
              {formatFileSize(node.size)}
            </span>
          )}

          {node.type === 'directory' && node.children && (
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--text-dim)',
              marginLeft: '12px'
            }}>
              {node.children.length} items
            </span>
          )}
        </div>

        {/* Children */}
        {node.type === 'directory' && isExpanded && node.children && (
          <div>
            {node.children.map((child, index) => (
              <FileTreeNode key={`${child.path}-${index}`} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  const filteredContents = useMemo(() => {
    if (!contents || !searchQuery) return contents;
    return filterNodes(contents, searchQuery);
  }, [contents, searchQuery]);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.95)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000
    }}>
      <div style={{
        background: 'var(--card-bg)',
        borderRadius: '12px',
        width: '80%',
        maxWidth: '900px',
        height: '80vh',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid var(--border)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.5rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--modal-header-bg)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, var(--accent), var(--accent-bright))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ fontSize: '1.5rem' }}>📦</span>
            </div>
            <div>
              <h2 style={{
                margin: 0,
                fontSize: '1.25rem',
                fontWeight: 600,
                color: 'var(--text-bright)'
              }}>
                Backup Contents
              </h2>
              <p style={{
                margin: 0,
                fontSize: '0.875rem',
                color: 'var(--text-dim)',
                marginTop: '0.25rem'
              }}>
                {projectName} • {backupPath.split('/').pop()}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-dim)',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--hover-bg)';
              e.currentTarget.style.color = 'var(--text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--text-dim)';
            }}
          >
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search Bar */}
        <div style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--border)',
          background: 'var(--search-bg)'
        }}>
          <div style={{
            position: 'relative',
            maxWidth: '400px'
          }}>
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 36px',
                background: 'var(--input-bg)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: 'var(--text)',
                fontSize: '0.875rem',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = 'var(--accent)'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
            />
            <svg
              width="16"
              height="16"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-dim)'
              }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-dim)',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* File Tree */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '0.5rem 0'
        }}>
          {loading && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-dim)'
            }}>
              <div style={{
                width: '40px',
                height: '40px',
                border: '3px solid var(--border)',
                borderTopColor: 'var(--accent)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              <p style={{ marginTop: '1rem' }}>Loading backup contents...</p>
            </div>
          )}

          {error && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--danger)'
            }}>
              <svg width="48" height="48" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <p style={{ marginTop: '1rem' }}>{error}</p>
              <button
                onClick={loadBackupContents}
                style={{
                  marginTop: '1rem',
                  padding: '8px 16px',
                  background: 'var(--accent)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && filteredContents && (
            <FileTreeNode node={filteredContents} depth={0} />
          )}

          {!loading && !error && filteredContents === null && searchQuery && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'var(--text-dim)'
            }}>
              <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <p style={{ marginTop: '1rem' }}>No files match "{searchQuery}"</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {selectedFile && (
          <div style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border)',
            background: 'var(--footer-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{
              fontSize: '0.875rem',
              color: 'var(--text-dim)',
              fontFamily: 'var(--mono)'
            }}>
              {selectedFile}
            </div>
            <button
              onClick={() => {
                (window as any).saviorAPI.extractFile({
                  backupPath,
                  filePath: selectedFile
                });
              }}
              style={{
                padding: '6px 12px',
                background: 'var(--accent)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <svg width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Extract File
            </button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default BackupContentsViewer;