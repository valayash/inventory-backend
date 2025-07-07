from django.shortcuts import render
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import transaction
import pandas as pd
import io

from .models import Frame, LensType
from .serializers import FrameSerializer, LensTypeSerializer


class FrameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing frames in the product catalog
    """
    queryset = Frame.objects.all()
    serializer_class = FrameSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['frame_type', 'color', 'material', 'brand']
    search_fields = ['name', 'product_id', 'brand']
    ordering_fields = ['name', 'price', 'brand']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """
        Get all frames for the product catalog display
        """
        frames = self.get_queryset()
        serializer = self.get_serializer(frames, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def choices(self, request):
        """
        Get available choices for filters - returns actual database values
        """
        # Get choices from database plus predefined choices
        db_choices = Frame.get_available_choices()
        
        # Combine predefined choices with database values for frontend display
        frame_type_choices = []
        color_choices = []
        material_choices = []
        
        # Add predefined choices with proper labels
        for choice in Frame.FRAME_TYPE_CHOICES:
            frame_type_choices.append({'value': choice[0], 'label': choice[1]})
        
        for choice in Frame.COLOR_CHOICES:
            color_choices.append({'value': choice[0], 'label': choice[1]})
            
        for choice in Frame.MATERIAL_CHOICES:
            material_choices.append({'value': choice[0], 'label': choice[1]})
        
        # Add any new values from database that aren't in predefined choices
        predefined_frame_types = [choice[0] for choice in Frame.FRAME_TYPE_CHOICES]
        predefined_colors = [choice[0] for choice in Frame.COLOR_CHOICES]
        predefined_materials = [choice[0] for choice in Frame.MATERIAL_CHOICES]
        
        for frame_type in db_choices['frame_types']:
            if frame_type and frame_type not in predefined_frame_types:
                frame_type_choices.append({'value': frame_type, 'label': frame_type.title()})
        
        for color in db_choices['colors']:
            if color and color not in predefined_colors:
                color_choices.append({'value': color, 'label': color.title()})
                
        for material in db_choices['materials']:
            if material and material not in predefined_materials:
                material_choices.append({'value': material, 'label': material.title()})
        
        return Response({
            'frame_types': frame_type_choices,
            'colors': color_choices,
            'materials': material_choices,
            'brands': db_choices['brands'],
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search functionality
        """
        query = request.query_params.get('q', '')
        if query:
            queryset = self.get_queryset().filter(
                Q(name__icontains=query) |
                Q(product_id__icontains=query) |
                Q(brand__icontains=query)
            )
        else:
            queryset = self.get_queryset()
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_csv(self, request):
        """
        Upload CSV file to bulk create/update frames
        Expected CSV format:
        frame_id,frame_name,frame_type,price,color,material,brand
        
        Now accepts any values for frame_type, color, and material
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        csv_file = request.FILES['file']
        
        # Check if it's a CSV file
        if not csv_file.name.endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Read CSV file
            csv_content = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Validate required columns
            required_columns = ['frame_id', 'frame_name', 'frame_type', 'price', 'color', 'material', 'brand']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return Response(
                    {'error': f'Missing required columns: {", ".join(missing_columns)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            errors = []
            created_count = 0
            updated_count = 0
            
            # Process each row
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Clean and normalize data
                        frame_type = str(row['frame_type']).strip().lower() if pd.notna(row['frame_type']) else ''
                        color = str(row['color']).strip().lower() if pd.notna(row['color']) else ''
                        material = str(row['material']).strip().lower() if pd.notna(row['material']) else ''
                        
                        # Validate required fields
                        if not frame_type:
                            errors.append(f"Row {index + 2}: frame_type cannot be empty")
                            continue
                            
                        if not color:
                            errors.append(f"Row {index + 2}: color cannot be empty")
                            continue
                            
                        if not material:
                            errors.append(f"Row {index + 2}: material cannot be empty")
                            continue
                        
                        # Validate price
                        try:
                            price = float(row['price']) if pd.notna(row['price']) else 0
                            if price < 0:
                                errors.append(f"Row {index + 2}: Price must be a positive number")
                                continue
                        except (ValueError, TypeError):
                            errors.append(f"Row {index + 2}: Invalid price format")
                            continue
                        
                        # Validate frame_id and frame_name
                        frame_id = str(row['frame_id']).strip() if pd.notna(row['frame_id']) else ''
                        frame_name = str(row['frame_name']).strip() if pd.notna(row['frame_name']) else ''
                        brand = str(row['brand']).strip() if pd.notna(row['brand']) else ''
                        
                        if not frame_id:
                            errors.append(f"Row {index + 2}: frame_id cannot be empty")
                            continue
                            
                        if not frame_name:
                            errors.append(f"Row {index + 2}: frame_name cannot be empty")
                            continue
                            
                        if not brand:
                            errors.append(f"Row {index + 2}: brand cannot be empty")
                            continue
                        
                        # Create or update frame
                        frame_data = {
                            'product_id': frame_id,
                            'name': frame_name,
                            'frame_type': frame_type,
                            'price': price,
                            'color': color,
                            'material': material,
                            'brand': brand,
                        }
                        
                        frame, created = Frame.objects.update_or_create(
                            product_id=frame_data['product_id'],
                            defaults=frame_data
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        continue
            
            # Prepare response
            response_data = {
                'success': True,
                'created': created_count,
                'updated': updated_count,
                'total_processed': created_count + updated_count,
            }
            
            if errors:
                response_data['errors'] = errors
                response_data['error_count'] = len(errors)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except pd.errors.EmptyDataError:
            return Response(
                {'error': 'CSV file is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except pd.errors.ParserError as e:
            return Response(
                {'error': f'Error parsing CSV file: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        """
        Download CSV template for bulk upload
        """
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="frames_template.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['frame_id', 'frame_name', 'frame_type', 'price', 'color', 'material', 'brand'])
        
        # Add some example rows with both traditional and new values
        writer.writerow(['F001', 'Classic Aviator', 'aviator', '129.99', 'gold', 'metal', 'Ray-Ban'])
        writer.writerow(['F002', 'Modern Square', 'square', '89.99', 'black', 'acetate', 'Oakley'])
        writer.writerow(['F003', 'Vintage Round', 'round', '159.99', 'tortoise', 'acetate', 'Persol'])
        writer.writerow(['F004', 'Sports Wrap', 'wrap-around', '199.99', 'neon-green', 'carbon-fiber', 'Nike'])
        writer.writerow(['F005', 'Designer Cat Eye', 'cat-eye', '249.99', 'rose-gold', 'titanium', 'Gucci'])
        
        return response

    @action(detail=False, methods=['get'])
    def by_product_id(self, request):
        """
        Get frame details by product_id (frame_id)
        """
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            frame = Frame.objects.get(product_id=product_id)
            serializer = self.get_serializer(frame)
            return Response(serializer.data)
        except Frame.DoesNotExist:
            return Response(
                {'error': 'Frame not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class LensTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing lens types
    """
    queryset = LensType.objects.all()
    serializer_class = LensTypeSerializer
    permission_classes = [IsAuthenticated]
