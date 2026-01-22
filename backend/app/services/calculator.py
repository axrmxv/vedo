import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from typing import Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CalculatorService:
    """Сервис для обработки файлов расчёта"""
    
    def __init__(self):
        # Вместимость форм из настроек
        self.FORM_CAPACITY = {
            1: settings.FORM_CAPACITY_1,
            2: settings.FORM_CAPACITY_2,
            3: settings.FORM_CAPACITY_3
        }
        # Типы отсечек из настроек
        self.CUTOFF_TYPES = {
            1: settings.CUTOFF_TYPE_1,
            2: settings.CUTOFF_TYPE_2,
            3: settings.CUTOFF_TYPE_3
        }
    
    def parse_item_name(self, item_name: str) -> dict:
        """
        Парсинг названия изделия
        
        Args:
            item_name: Название в формате name_WxLxP_F
            
        Returns:
            dict: Словарь с параметрами изделия
        """
        match = re.match(r'(\w+)_(\d+)x(\d+)x(\d+)_(\d+)', item_name)
        if not match:
            raise ValueError(f"Некорректный формат названия: {item_name}")
        
        name, width, length, projection, form_type = match.groups()
        return {
            'name': name,
            'width_mm': int(width),
            'length_mm': int(length),
            'projection_mm': int(projection),
            'form_type': int(form_type)
        }
    
    def parse_txt_file(self, content: str) -> pd.DataFrame:
        """
        Парсинг TXT файла
        
        Args:
            content: Содержимое файла
            
        Returns:
            DataFrame: Датафрейм с данными
        """
        logger.info("Парсинг TXT файла")
        items = []
        lines = content.strip().split('\n')
        for line in lines:
            parts = line.strip().split()
            items.extend(parts)
        
        data = []
        item_counts = {}
        
        for item in items:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        for item_name, count in item_counts.items():
            parsed = self.parse_item_name(item_name)
            width_m = parsed['width_mm'] / 1000
            length_m = parsed['length_mm'] / 1000
            projection_m = parsed['projection_mm'] / 1000
            
            record = {
                'Наименование изделия': f"{parsed['name']}_{parsed['width_mm']}x{parsed['length_mm']}",
                'Ед. изм.': 'шт.',
                'Количество': count,
                'Ширина, м': round(width_m, 2),
                'Длина, м': round(length_m, 2),
                'Проекция, м': round(projection_m, 2),
                'Тип формы': parsed['form_type'],
                'width_mm': parsed['width_mm'],
                'length_mm': parsed['length_mm']
            }
            data.append(record)
        
        logger.info(f"Загружено из TXT: {len(data)} позиций")
        return pd.DataFrame(data)
    
    def parse_xlsx_file(self, file_path: Path) -> pd.DataFrame:
        """
        Парсинг XLSX файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            DataFrame: Датафрейм с данными
        """
        logger.info("Парсинг XLSX файла")
        df = pd.read_excel(file_path)
        df = df.copy()
        df = df.rename(columns={'Кол-во': 'Количество'})
        df['width_mm'] = (df['Ширина, м'] * 1000).astype(int)
        df['length_mm'] = (df['Длина, м'] * 1000).astype(int)
        
        result = df[[
            'Наименование изделия',
            'Ед. изм.',
            'Количество',
            'Ширина, м',
            'Длина, м',
            'Проекция, м',
            'Тип формы',
            'width_mm',
            'length_mm'
        ]]
        
        logger.info(f"Загружено из XLSX: {len(result)} позиций")
        return result
    
    def assign_cutoffs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Назначение отсечек
        
        Args:
            df: Входной датафрейм
            
        Returns:
            DataFrame: Датафрейм с отсечками
        """
        logger.info("Назначение отсечек")
        df = df.sort_values(
            ['Тип формы', 'width_mm', 'Длина, м'],
            ascending=[True, True, False]
        )
        
        new_rows = []
        cutoff_counter = 1
        
        for (form_type, width_mm), group in df.groupby(['Тип формы', 'width_mm']):
            group = group.copy().reset_index(drop=True)
            capacity = self.FORM_CAPACITY[form_type]
            cutoff_type = self.CUTOFF_TYPES[form_type]
            
            subgroups = []
            current_subgroup = []
            current_total = 0
            
            for _, row in group.iterrows():
                count = int(row['Количество'])
                if current_total + count > capacity:
                    if current_subgroup:
                        subgroups.append(current_subgroup)
                    current_subgroup = [row]
                    current_total = count
                else:
                    current_subgroup.append(row)
                    current_total += count
            
            if current_subgroup:
                subgroups.append(current_subgroup)
            
            for subgroup in subgroups:
                max_length_idx = max(
                    range(len(subgroup)),
                    key=lambda i: subgroup[i]['Длина, м']
                )
                for i, row in enumerate(subgroup):
                    row_dict = row.to_dict()
                    row_dict['Отсечка'] = cutoff_counter
                    row_dict['Тип отсечки'] = 0 if i == max_length_idx else cutoff_type
                    new_rows.append(row_dict)
                cutoff_counter += 1
        
        result_df = pd.DataFrame(new_rows)
        logger.info(f"Создано отсечек: {cutoff_counter - 1}")
        return result_df.drop(['width_mm', 'length_mm'], axis=1, errors='ignore')
    
    def calculate_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Расчёт производных колонок
        
        Args:
            df: Входной датафрейм
            
        Returns:
            DataFrame: Датафрейм с расчётами
        """
        logger.info("Расчёт производных колонок")
        df['Развертка, м'] = round(df['Ширина, м'] * df['Длина, м'], 2)
        df['Общая площадь, м'] = round(df['Развертка, м'] * df['Количество'], 2)
        df['Площадь проекции, м'] = round(
            df['Длина, м'] * df['Проекция, м'] * df['Количество'], 2
        )
        return df
    
    def reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Упорядочивание колонок
        
        Args:
            df: Входной датафрейм
            
        Returns:
            DataFrame: Датафрейм с упорядоченными колонками
        """
        return df[[
            'Наименование изделия', 'Ед. изм.', 'Количество', 'Ширина, м', 'Длина, м',
            'Развертка, м', 'Общая площадь, м',
            'Проекция, м', 'Площадь проекции, м',
            'Тип формы', 'Отсечка', 'Тип отсечки'
        ]]
    
    async def process_file(self, file_path: Path, file_extension: str, content: Union[str, None] = None) -> pd.DataFrame:
        """
        Обработка файла
        
        Args:
            file_path: Путь к файлу
            file_extension: Расширение файла (.txt или .xlsx)
            content: Содержимое TXT файла (опционально)
            
        Returns:
            DataFrame: Обработанный датафрейм
        """
        logger.info(f"Начало обработки файла: {file_path}")
        
        try:
            if file_extension == '.txt':
                if content is None:
                    raise ValueError("Для TXT файла требуется содержимое")
                df = self.parse_txt_file(content)
            elif file_extension == '.xlsx':
                df = self.parse_xlsx_file(file_path)
            else:
                raise ValueError(f"Неподдерживаемое расширение: {file_extension}")
            
            df = self.assign_cutoffs(df)
            df = self.calculate_derived_columns(df)
            df = self.reorder_columns(df)
            
            logger.info("Обработка файла завершена успешно")
            return df
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
            raise


# Singleton instance
calculator_service = CalculatorService()
