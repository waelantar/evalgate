import * as Select from '@radix-ui/react-select'

export type PickerOption = Readonly<{ value: string; label: string; detail?: string }>

type PickerProps = Readonly<{
  id: string
  label: string
  value: string
  options: readonly PickerOption[]
  onChange: (value: string) => void
  disabled?: boolean
  emptyLabel?: string
}>

export function Picker({ id, label, value, options, onChange, disabled = false, emptyLabel = 'No options available' }: PickerProps) {
  return <div className="picker">
    <span id={`${id}-label`} className="picker-label">{label}</span>
    <Select.Root value={value} onValueChange={onChange} disabled={disabled || options.length === 0}>
      <Select.Trigger id={id} className="picker-trigger" aria-label={label}>
        <Select.Value id={`${id}-value`} placeholder={emptyLabel} />
        <Select.Icon className="picker-chevron" aria-hidden="true">v</Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="picker-menu" position="popper" sideOffset={6}>
          <Select.Viewport className="picker-viewport">
            {options.map((option) => <Select.Item key={option.value} value={option.value} className="picker-option">
              <Select.ItemText>{option.label}</Select.ItemText>
              {option.detail ? <small>{option.detail}</small> : null}
              <Select.ItemIndicator className="picker-indicator" aria-hidden="true">selected</Select.ItemIndicator>
            </Select.Item>)}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  </div>
}
